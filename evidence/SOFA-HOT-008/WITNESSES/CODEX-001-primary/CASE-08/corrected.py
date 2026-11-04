"""Bounded, starvation-free SPN2 scheduling model for deterministic testing."""

import heapq
import json
import urllib.error
from collections import deque
from dataclasses import dataclass, field
from enum import Enum


class State(str, Enum):
    QUEUED = "queued"
    SUBMITTING = "submitting"
    INFLIGHT = "inflight"
    RETRY_WAIT = "retry_wait"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass
class Task:
    url: str
    state: State = State.QUEUED
    submit_attempts: int = 0
    poll_errors: int = 0
    job_id: str | None = None
    next_deadline: float = 0.0
    terminal_detail: str | None = None
    transitions: list[str] = field(default_factory=lambda: [State.QUEUED.value])

    def move(self, state, detail=None):
        self.state = state
        self.transitions.append(state.value)
        if detail is not None:
            self.terminal_detail = detail


def _retry_after(exc, fallback):
    raw = exc.headers.get("Retry-After") if exc.headers else None
    try:
        parsed = float(raw)
        if parsed >= 0:
            return parsed
    except (TypeError, ValueError):
        pass
    return float(fallback)


class Scheduler:
    def __init__(self, api, clock, concurrency=3, poll_interval=15,
                 max_submit_attempts=3, max_poll_errors=3, max_operations=1000):
        self.api = api
        self.clock = clock
        self.concurrency = concurrency
        self.poll_interval = float(poll_interval)
        self.max_submit_attempts = max_submit_attempts
        self.max_poll_errors = max_poll_errors
        self.max_operations = max_operations
        self.operations = 0
        self._serial = 0

    def _bump(self):
        self.operations += 1
        if self.operations > self.max_operations:
            raise RuntimeError("reference scheduler operation ceiling reached")

    def _delay(self, delayed, task, seconds):
        task.next_deadline = self.clock.monotonic() + seconds
        task.move(State.RETRY_WAIT)
        self._serial += 1
        heapq.heappush(delayed, (task.next_deadline, self._serial, task))

    def run(self, urls):
        seen = set()
        tasks = []
        ready = deque()
        for url in urls:
            if url in seen:
                continue
            seen.add(url)
            task = Task(url)
            tasks.append(task)
            ready.append(task)

        delayed = []
        inflight = {}
        while any(task.state not in (State.SUCCEEDED, State.FAILED) for task in tasks):
            now = self.clock.monotonic()
            while delayed and delayed[0][0] <= now:
                _, _, task = heapq.heappop(delayed)
                task.move(State.QUEUED)
                ready.append(task)

            # Poll due work first, so submission backoff can never starve it.
            for job_id, task in sorted(list(inflight.items())):
                if task.next_deadline > now:
                    continue
                self._bump()
                try:
                    status = json.loads(self.api.status(job_id).read())
                except urllib.error.HTTPError as exc:
                    if exc.code not in (429, 503):
                        raise
                    task.poll_errors += 1
                    if task.poll_errors >= self.max_poll_errors:
                        del inflight[job_id]
                        task.move(State.FAILED, f"poll_http_{exc.code}_ceiling")
                    else:
                        task.next_deadline = now + _retry_after(
                            exc, min(2 ** (task.poll_errors - 1), 60)
                        )
                    continue

                value = status.get("status")
                if value == "pending":
                    task.next_deadline = now + self.poll_interval
                elif value == "success":
                    del inflight[job_id]
                    task.move(State.SUCCEEDED, "success")
                elif value == "error":
                    del inflight[job_id]
                    task.move(State.FAILED, "remote_error")
                else:
                    del inflight[job_id]
                    task.move(State.FAILED, "unknown_status")

            while ready and len(inflight) < self.concurrency:
                task = ready.popleft()
                task.move(State.SUBMITTING)
                task.submit_attempts += 1
                self._bump()
                try:
                    response = json.loads(self.api.submit(
                        task.url,
                        {"url": task.url, "if_not_archived_within": "30d"},
                    ).read())
                except urllib.error.HTTPError as exc:
                    if exc.code not in (429, 503):
                        raise
                    if task.submit_attempts >= self.max_submit_attempts:
                        task.move(State.FAILED, f"submit_http_{exc.code}_ceiling")
                    else:
                        delay = _retry_after(
                            exc, min(2 ** (task.submit_attempts - 1), 60)
                        )
                        self._delay(delayed, task, delay)
                    continue

                job_id = response.get("job_id")
                if not job_id:
                    if task.submit_attempts >= self.max_submit_attempts:
                        task.move(State.FAILED, "missing_job_id_ceiling")
                    else:
                        self._delay(delayed, task,
                                    min(2 ** (task.submit_attempts - 1), 60))
                    continue
                task.job_id = job_id
                task.next_deadline = now + self.poll_interval
                task.move(State.INFLIGHT)
                inflight[job_id] = task

            if all(task.state in (State.SUCCEEDED, State.FAILED) for task in tasks):
                break
            deadlines = [deadline for deadline, _, _ in delayed]
            deadlines.extend(task.next_deadline for task in inflight.values())
            if not deadlines:
                raise RuntimeError("nonterminal task has no deadline")
            next_deadline = min(deadlines)
            self.clock.sleep(max(0.0, next_deadline - self.clock.monotonic()))
        return tasks
