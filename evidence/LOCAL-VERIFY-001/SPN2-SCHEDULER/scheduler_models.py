#!/usr/bin/env python3
"""Offline SPN2 scheduler models for LOCAL-VERIFY-001.

No class in this module performs I/O or sleeps.  Fake responses and a virtual
clock make every trace bounded and deterministic.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from enum import StrEnum
import heapq
from typing import Any, Iterable


class State(StrEnum):
    QUEUED = "QUEUED"
    SUBMITTING = "SUBMITTING"
    ACCEPTED = "ACCEPTED"
    PENDING = "PENDING"
    SUCCEEDED_UNVERIFIED = "SUCCEEDED_UNVERIFIED"
    VERIFIED = "VERIFIED"
    FAILED_RETRYABLE = "FAILED_RETRYABLE"
    FAILED_PERMANENT = "FAILED_PERMANENT"
    UNCERTAIN_ACCEPTANCE = "UNCERTAIN_ACCEPTANCE"


@dataclass(frozen=True)
class SubmitEvent:
    kind: str
    job_id: str | None = None
    retry_after: float | None = None
    server_accepted: bool = False
    body: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PollEvent:
    status: str
    timestamp: str | None = None
    retry_after: float | None = None


@dataclass
class VirtualClock:
    now: float = 0.0
    advances: list[dict[str, float]] = field(default_factory=list)

    def advance_to(self, target: float) -> None:
        if target < self.now:
            raise ValueError(f"clock cannot move backward: {self.now} -> {target}")
        if target > self.now:
            self.advances.append({"from": self.now, "to": target})
            self.now = target

    def sleep(self, seconds: float) -> None:
        if seconds < 0:
            raise ValueError("negative sleep")
        self.advance_to(self.now + seconds)


class FakeHTTPError(Exception):
    def __init__(
        self,
        status: int,
        *,
        retry_after: float | None = None,
        acceptance_uncertain: bool = False,
        message: str = "",
    ) -> None:
        super().__init__(message or f"HTTP {status}")
        self.status = status
        self.retry_after = retry_after
        self.acceptance_uncertain = acceptance_uncertain


class FakeSPN2API:
    """Scripted fake API. Every missing script entry is a test failure."""

    def __init__(
        self,
        *,
        submit: dict[str, Iterable[SubmitEvent]] | None = None,
        poll: dict[str, Iterable[PollEvent]] | None = None,
        lookup: dict[str, Iterable[bool]] | None = None,
        reconcile: dict[str, Iterable[str | None]] | None = None,
    ) -> None:
        self.submit_scripts = {key: deque(value) for key, value in (submit or {}).items()}
        self.poll_scripts = {key: deque(value) for key, value in (poll or {}).items()}
        self.lookup_scripts = {key: deque(value) for key, value in (lookup or {}).items()}
        self.reconcile_scripts = {key: deque(value) for key, value in (reconcile or {}).items()}
        self.call_log: list[dict[str, Any]] = []
        self.server_jobs: dict[str, str] = {}

    @staticmethod
    def _take(mapping: dict[str, deque[Any]], key: str, operation: str) -> Any:
        if key not in mapping or not mapping[key]:
            raise AssertionError(f"unscripted {operation} for {key}")
        return mapping[key].popleft()

    def submit(self, url: str, now: float) -> dict[str, Any]:
        event: SubmitEvent = self._take(self.submit_scripts, url, "submit")
        self.call_log.append({"operation": "submit", "url": url, "time": now, "kind": event.kind})
        if event.server_accepted:
            if not event.job_id:
                raise AssertionError("server_accepted event requires internal job_id")
            self.server_jobs[event.job_id] = url
        if event.kind == "accepted":
            if not event.job_id:
                raise AssertionError("accepted event requires job_id")
            self.server_jobs[event.job_id] = url
            return {"job_id": event.job_id, **event.body}
        if event.kind == "http_429":
            raise FakeHTTPError(429, retry_after=event.retry_after)
        if event.kind == "http_503":
            raise FakeHTTPError(
                503, retry_after=event.retry_after,
                acceptance_uncertain=True,
            )
        if event.kind == "missing_job_id":
            return dict(event.body)
        if event.kind == "rejected":
            raise FakeHTTPError(400, acceptance_uncertain=False)
        raise AssertionError(f"unknown submit event: {event.kind}")

    def poll(self, job_id: str, now: float) -> dict[str, Any]:
        event: PollEvent = self._take(self.poll_scripts, job_id, "poll")
        self.call_log.append({"operation": "poll", "job_id": job_id, "time": now, "status": event.status})
        if event.status == "http_503":
            raise FakeHTTPError(503, retry_after=event.retry_after)
        body: dict[str, Any] = {"status": event.status}
        if event.timestamp is not None:
            body["timestamp"] = event.timestamp
        return body

    def lookup(self, url: str, timestamp: str, now: float) -> bool:
        found: bool = self._take(self.lookup_scripts, url, "lookup")
        self.call_log.append({
            "operation": "lookup", "url": url, "timestamp": timestamp,
            "time": now, "found": found,
        })
        return found

    def reconcile(self, url: str, now: float) -> str | None:
        result: str | None = self._take(self.reconcile_scripts, url, "reconcile")
        self.call_log.append({"operation": "reconcile", "url": url, "time": now, "job_id": result})
        return result


@dataclass
class Task:
    task_id: str
    url: str
    state: State = State.QUEUED
    job_id: str | None = None
    timestamp: str | None = None
    submit_attempts: int = 0
    poll_attempts: int = 0
    verify_attempts: int = 0
    reconcile_attempts: int = 0
    retry_kind: str | None = None
    poll_at: float | None = None
    verify_at: float | None = None
    reconcile_at: float | None = None
    manual_intervention: bool = False
    reason: str | None = None
    history: deque[dict[str, Any]] = field(default_factory=lambda: deque(maxlen=64))

    def transition(self, state: State, now: float, reason: str) -> None:
        self.state = state
        self.reason = reason
        self.history.append({"time": now, "state": state.value, "reason": reason})


class BrokenPostedLoop:
    """The capacity-fill loop from the post, bounded only by a test ceiling."""

    def __init__(self, api: FakeSPN2API, clock: VirtualClock, *, concurrency: int, backoff: float) -> None:
        self.api = api
        self.clock = clock
        self.concurrency = concurrency
        self.backoff = backoff
        self.queue_front_shift_cost = 0
        self.submit_attempts = 0
        self.poll_attempts = 0

    def run(
        self,
        queue: list[str],
        inflight: dict[str, str],
        *,
        capacity_iteration_ceiling: int,
    ) -> dict[str, Any]:
        capacity_iterations = 0
        while queue or inflight:
            while queue and len(inflight) < self.concurrency:
                if capacity_iterations >= capacity_iteration_ceiling:
                    return self._result(queue, inflight, capacity_iterations, "ceiling_inside_capacity_loop")
                capacity_iterations += 1
                self.queue_front_shift_cost += max(0, len(queue) - 1)
                url = queue.pop(0)
                self.submit_attempts += 1
                try:
                    body = self.api.submit(url, self.clock.now)
                except FakeHTTPError as exc:
                    if exc.status in (429, 503):
                        self.queue_front_shift_cost += len(queue)
                        queue.insert(0, url)
                        self.clock.sleep(self.backoff)
                        continue
                    raise
                job_id = body.get("job_id")
                if job_id:
                    inflight[job_id] = url
            self.clock.sleep(15)
            for job_id, url in list(inflight.items()):
                self.poll_attempts += 1
                status = self.api.poll(job_id, self.clock.now)
                if status.get("status") != "pending":
                    del inflight[job_id]
        return self._result(queue, inflight, capacity_iterations, "completed")

    def _result(
        self,
        queue: list[str],
        inflight: dict[str, str],
        iterations: int,
        stop_reason: str,
    ) -> dict[str, Any]:
        return {
            "stop_reason": stop_reason,
            "capacity_iterations": iterations,
            "submission_attempts": self.submit_attempts,
            "polling_attempts": self.poll_attempts,
            "virtual_elapsed": self.clock.now,
            "queue": list(queue),
            "inflight": dict(inflight),
            "queue_front_shift_cost": self.queue_front_shift_cost,
        }


class FairScheduler:
    """Poll-first, deadline-driven, bounded offline scheduler."""

    def __init__(
        self,
        api: FakeSPN2API,
        clock: VirtualClock,
        *,
        concurrency: int = 3,
        poll_interval: float = 15,
        default_backoff: float = 900,
        reconcile_interval: float = 30,
        verify_interval: float = 20,
        max_submit_attempts: int = 3,
        max_poll_attempts: int = 5,
        max_reconcile_attempts: int = 3,
        max_verify_attempts: int = 3,
    ) -> None:
        if concurrency < 1:
            raise ValueError("concurrency must be positive")
        self.api = api
        self.clock = clock
        self.concurrency = concurrency
        self.poll_interval = poll_interval
        self.default_backoff = default_backoff
        self.reconcile_interval = reconcile_interval
        self.verify_interval = verify_interval
        self.max_submit_attempts = max_submit_attempts
        self.max_poll_attempts = max_poll_attempts
        self.max_reconcile_attempts = max_reconcile_attempts
        self.max_verify_attempts = max_verify_attempts
        self.tasks: dict[str, Task] = {}
        self.ready: deque[str] = deque()
        self.delayed_submit: list[tuple[float, int, str]] = []
        self.sequence = 0
        self.steps = 0
        self.max_ready_length = 0
        self.max_delayed_length = 0
        self.action_log: list[dict[str, Any]] = []

    def add_queued(self, task_id: str, url: str) -> Task:
        if task_id in self.tasks:
            raise ValueError(f"duplicate task id: {task_id}")
        task = Task(task_id, url)
        task.transition(State.QUEUED, self.clock.now, "input_admitted")
        self.tasks[task_id] = task
        self.ready.append(task_id)
        self._update_bounds()
        return task

    def add_existing(self, task_id: str, url: str, job_id: str, *, poll_at: float = 0) -> Task:
        if task_id in self.tasks:
            raise ValueError(f"duplicate task id: {task_id}")
        task = Task(task_id, url, job_id=job_id, poll_at=poll_at)
        task.transition(State.ACCEPTED, self.clock.now, "existing_inflight")
        task.transition(State.PENDING, self.clock.now, "poll_scheduled")
        self.tasks[task_id] = task
        return task

    def active_admissions(self) -> int:
        active = {State.ACCEPTED, State.PENDING, State.UNCERTAIN_ACCEPTANCE}
        return sum(
            task.state in active
            or (
                task.state == State.FAILED_RETRYABLE
                and task.retry_kind == "poll"
                and task.job_id is not None
            )
            for task in self.tasks.values()
        )

    def _update_bounds(self) -> None:
        self.max_ready_length = max(self.max_ready_length, len(self.ready))
        self.max_delayed_length = max(self.max_delayed_length, len(self.delayed_submit))

    def _delay_submit(self, task: Task, deadline: float) -> None:
        self.sequence += 1
        heapq.heappush(self.delayed_submit, (deadline, self.sequence, task.task_id))
        self._update_bounds()

    def _promote_submissions(self) -> None:
        while self.delayed_submit and self.delayed_submit[0][0] <= self.clock.now:
            _, _, task_id = heapq.heappop(self.delayed_submit)
            task = self.tasks[task_id]
            if task.state == State.FAILED_RETRYABLE and task.retry_kind == "submit":
                task.transition(State.QUEUED, self.clock.now, "submit_deadline_due")
                self.ready.append(task_id)
        self._update_bounds()

    def _due(self, attr: str, states: set[State]) -> list[Task]:
        candidates = [
            task for task in self.tasks.values()
            if task.state in states
            and getattr(task, attr) is not None
            and getattr(task, attr) <= self.clock.now
        ]
        return sorted(candidates, key=lambda task: (getattr(task, attr), task.task_id))

    def _next_deadline(self) -> float | None:
        values: list[float] = []
        if self.delayed_submit:
            values.append(self.delayed_submit[0][0])
        for task in self.tasks.values():
            for attr in ("poll_at", "verify_at", "reconcile_at"):
                value = getattr(task, attr)
                if value is not None:
                    values.append(value)
        return min(values) if values else None

    def run(self, *, max_steps: int = 1000) -> dict[str, Any]:
        while self.steps < max_steps:
            self._promote_submissions()

            # Poll known in-flight work before spending admission budget.
            due_poll = self._due("poll_at", {State.ACCEPTED, State.PENDING, State.FAILED_RETRYABLE})
            due_poll = [
                task for task in due_poll
                if task.state in {State.ACCEPTED, State.PENDING} or task.retry_kind == "poll"
            ]
            if due_poll:
                self._poll(due_poll[0])
                continue

            due_verify = self._due("verify_at", {State.SUCCEEDED_UNVERIFIED})
            if due_verify:
                self._verify(due_verify[0])
                continue

            due_reconcile = self._due("reconcile_at", {State.UNCERTAIN_ACCEPTANCE})
            if due_reconcile:
                self._reconcile(due_reconcile[0])
                continue

            if self.ready and self.active_admissions() < self.concurrency:
                task_id = self.ready.popleft()
                task = self.tasks[task_id]
                if task.state == State.QUEUED:
                    self._submit(task)
                    continue

            deadline = self._next_deadline()
            if deadline is None:
                break
            if deadline <= self.clock.now:
                raise AssertionError("due deadline was not serviceable")
            self.clock.advance_to(deadline)

        stopped_by_ceiling = self.steps >= max_steps
        return {
            "steps": self.steps,
            "stopped_by_ceiling": stopped_by_ceiling,
            "virtual_elapsed": self.clock.now,
            "max_ready_length": self.max_ready_length,
            "max_delayed_length": self.max_delayed_length,
            "actions": list(self.action_log),
            "tasks": {task_id: self._task_summary(task) for task_id, task in sorted(self.tasks.items())},
        }

    def _record_action(self, operation: str, task: Task, **extra: Any) -> None:
        self.steps += 1
        self.action_log.append({
            "step": self.steps, "time": self.clock.now,
            "operation": operation, "task_id": task.task_id,
            **extra,
        })

    def _submit(self, task: Task) -> None:
        task.transition(State.SUBMITTING, self.clock.now, "submit_started")
        task.submit_attempts += 1
        self._record_action("submit", task, attempt=task.submit_attempts)
        try:
            body = self.api.submit(task.url, self.clock.now)
        except FakeHTTPError as exc:
            if exc.status == 429:
                if task.submit_attempts >= self.max_submit_attempts:
                    task.transition(State.FAILED_PERMANENT, self.clock.now, "submit_retry_ceiling_429")
                    return
                delay = exc.retry_after if exc.retry_after is not None else self.default_backoff
                task.retry_kind = "submit"
                task.transition(State.FAILED_RETRYABLE, self.clock.now, f"http_429_retry_after_{delay:g}")
                self._delay_submit(task, self.clock.now + delay)
                return
            if exc.status == 503 or exc.acceptance_uncertain:
                task.transition(State.UNCERTAIN_ACCEPTANCE, self.clock.now, "http_503_acceptance_unknown")
                task.reconcile_at = self.clock.now + self.reconcile_interval
                return
            task.transition(State.FAILED_PERMANENT, self.clock.now, f"submit_http_{exc.status}")
            return

        job_id = body.get("job_id")
        if not isinstance(job_id, str) or not job_id.strip():
            if body.get("accepted") is False or body.get("status") in {"rejected", "error"}:
                task.transition(
                    State.FAILED_PERMANENT, self.clock.now,
                    "protocol_invalid_missing_job_id_explicit_rejection",
                )
                return
            task.transition(
                State.UNCERTAIN_ACCEPTANCE, self.clock.now,
                "protocol_invalid_missing_job_id_acceptance_unknown",
            )
            task.reconcile_at = self.clock.now + self.reconcile_interval
            return
        task.job_id = job_id
        task.transition(State.ACCEPTED, self.clock.now, "job_id_received")
        task.poll_at = self.clock.now

    def _poll(self, task: Task) -> None:
        if not task.job_id:
            raise AssertionError("poll task lacks job_id")
        task.poll_at = None
        task.poll_attempts += 1
        self._record_action("poll", task, attempt=task.poll_attempts, job_id=task.job_id)
        try:
            body = self.api.poll(task.job_id, self.clock.now)
        except FakeHTTPError as exc:
            if task.poll_attempts >= self.max_poll_attempts:
                task.transition(State.FAILED_PERMANENT, self.clock.now, "poll_retry_ceiling")
                return
            delay = exc.retry_after if exc.retry_after is not None else self.poll_interval
            task.retry_kind = "poll"
            task.transition(State.FAILED_RETRYABLE, self.clock.now, f"poll_http_{exc.status}")
            task.poll_at = self.clock.now + delay
            return

        status = body.get("status")
        if status == "pending":
            task.retry_kind = None
            if task.poll_attempts >= self.max_poll_attempts:
                task.manual_intervention = True
                task.transition(
                    State.PENDING,
                    self.clock.now,
                    "server_pending_poll_ceiling_manual_intervention",
                )
                return
            task.transition(State.PENDING, self.clock.now, "server_pending")
            task.poll_at = self.clock.now + self.poll_interval
            return
        if status == "success" and isinstance(body.get("timestamp"), str):
            task.timestamp = body["timestamp"]
            task.transition(State.SUCCEEDED_UNVERIFIED, self.clock.now, "server_success_requires_index_check")
            task.verify_at = self.clock.now
            return
        if status in {"error", "failed"}:
            task.transition(State.FAILED_PERMANENT, self.clock.now, f"server_status_{status}")
            return

        if task.poll_attempts >= self.max_poll_attempts:
            task.transition(State.FAILED_PERMANENT, self.clock.now, f"unknown_status_{status!r}_ceiling")
            return
        task.retry_kind = "poll"
        task.transition(State.FAILED_RETRYABLE, self.clock.now, f"unknown_status_{status!r}")
        task.poll_at = self.clock.now + self.poll_interval

    def _verify(self, task: Task) -> None:
        if not task.timestamp:
            raise AssertionError("verification task lacks timestamp")
        task.verify_at = None
        task.verify_attempts += 1
        self._record_action("verify", task, attempt=task.verify_attempts)
        if self.api.lookup(task.url, task.timestamp, self.clock.now):
            task.transition(State.VERIFIED, self.clock.now, "capture_found_in_independent_index")
            return
        task.transition(State.SUCCEEDED_UNVERIFIED, self.clock.now, "capture_not_yet_in_index")
        if task.verify_attempts >= self.max_verify_attempts:
            task.manual_intervention = True
            return
        task.verify_at = self.clock.now + self.verify_interval

    def _reconcile(self, task: Task) -> None:
        task.reconcile_at = None
        task.reconcile_attempts += 1
        self._record_action("reconcile", task, attempt=task.reconcile_attempts)
        job_id = self.api.reconcile(task.url, self.clock.now)
        if isinstance(job_id, str) and job_id:
            task.job_id = job_id
            task.transition(State.ACCEPTED, self.clock.now, "reconciliation_found_job")
            task.poll_at = self.clock.now
            return
        task.transition(State.UNCERTAIN_ACCEPTANCE, self.clock.now, "reconciliation_no_job")
        if task.reconcile_attempts >= self.max_reconcile_attempts:
            task.manual_intervention = True
            return
        task.reconcile_at = self.clock.now + self.reconcile_interval

    @staticmethod
    def _task_summary(task: Task) -> dict[str, Any]:
        return {
            "url": task.url,
            "state": task.state.value,
            "job_id": task.job_id,
            "timestamp": task.timestamp,
            "submit_attempts": task.submit_attempts,
            "poll_attempts": task.poll_attempts,
            "verify_attempts": task.verify_attempts,
            "reconcile_attempts": task.reconcile_attempts,
            "manual_intervention": task.manual_intervention,
            "reason": task.reason,
            "retry_kind": task.retry_kind,
            "poll_at": task.poll_at,
            "verify_at": task.verify_at,
            "reconcile_at": task.reconcile_at,
            "history": list(task.history),
        }


class AccountQuota:
    """Synthetic account-wide admission model shared by independent workers."""

    def __init__(self, limit: int) -> None:
        self.limit = limit
        self.active: dict[str, tuple[str, str]] = {}
        self.urls: dict[str, str] = {}
        self.rejections = 0
        self.next_job = 1

    def submit(self, worker: str, url: str) -> str:
        if len(self.active) >= self.limit:
            self.rejections += 1
            raise FakeHTTPError(429, retry_after=10)
        job_id = f"shared-{self.next_job}"
        self.next_job += 1
        self.active[job_id] = (worker, url)
        self.urls[url] = job_id
        return job_id

    def finish(self, job_id: str) -> None:
        self.active.pop(job_id)


class AdmissionCoordinator:
    """Lease-based account admission plus duplicate-URL suppression."""

    def __init__(self, limit: int, lease_seconds: float) -> None:
        self.limit = limit
        self.lease_seconds = lease_seconds
        self.leases: dict[str, tuple[str, str, float]] = {}
        self.known_urls: set[str] = set()
        self.acquisition_serial = 0

    def _expire(self, now: float) -> None:
        for token, (_, url, deadline) in list(self.leases.items()):
            if deadline <= now:
                del self.leases[token]
                self.known_urls.discard(url)

    def acquire(self, worker: str, url: str, now: float) -> tuple[str, str | None]:
        self._expire(now)
        if url in self.known_urls:
            return "DUPLICATE", None
        if len(self.leases) >= self.limit:
            return "WAIT", None
        self.acquisition_serial += 1
        token = f"lease-{worker}-{self.acquisition_serial}"
        self.leases[token] = (worker, url, now + self.lease_seconds)
        self.known_urls.add(url)
        return "ACQUIRED", token

    def release(self, token: str, *, retain_url: bool = True) -> None:
        _, url, _ = self.leases.pop(token)
        if not retain_url:
            self.known_urls.discard(url)


class ShiftCountingList:
    def __init__(self, values: Iterable[int]) -> None:
        self.values = list(values)
        self.element_shifts = 0
        self.operations = 0

    def pop_front(self) -> int:
        self.operations += 1
        self.element_shifts += max(0, len(self.values) - 1)
        return self.values.pop(0)


class ComparisonCounter:
    comparisons = 0

    def __init__(self, deadline: int, serial: int) -> None:
        self.deadline = deadline
        self.serial = serial

    def __lt__(self, other: ComparisonCounter) -> bool:
        type(self).comparisons += 1
        return (self.deadline, self.serial) < (other.deadline, other.serial)


def operation_counts(backlog: int) -> dict[str, int]:
    front = ShiftCountingList(range(backlog))
    while front.values:
        front.pop_front()

    ready = deque(range(backlog))
    deque_ops = 0
    while ready:
        ready.popleft()
        deque_ops += 1

    ComparisonCounter.comparisons = 0
    heap: list[ComparisonCounter] = []
    for serial in range(backlog):
        # Reverse deadlines are adversarial for heap insertion.
        heapq.heappush(heap, ComparisonCounter(backlog - serial, serial))
    while heap:
        heapq.heappop(heap)

    # A fixed-tick scanner checks every task at every tick. A deadline heap
    # touches each item at insertion/removal and orders it with comparisons.
    fixed_tick_scans = backlog * backlog
    return {
        "backlog": backlog,
        "list_front_operations": front.operations,
        "list_element_shifts": front.element_shifts,
        "deque_front_operations": deque_ops,
        "deque_element_shifts": 0,
        "fixed_tick_deadline_checks": fixed_tick_scans,
        "heap_comparisons": ComparisonCounter.comparisons,
        "heap_pushes_plus_pops": 2 * backlog,
    }
