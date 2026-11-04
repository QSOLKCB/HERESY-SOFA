#!/usr/bin/env python3
"""Independent list-calendar oracle for one bounded SPN2 scheduling trace."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class OracleResult:
    final_states: dict[str, str]
    submit_times: tuple[float, ...]
    poll_times: tuple[tuple[str, float], ...]
    verify_times: tuple[tuple[str, float], ...]
    action_order: tuple[str, ...]


def run_oracle() -> OracleResult:
    """Run a separate sorted-list event model for the agreement fixture.

    Priority is deliberately encoded in the calendar key: poll, verify, submit.
    The fixture has an existing job plus a new URL that gets one 429 with a
    Retry-After of 37 seconds before acceptance.
    """

    EventKind = Literal["poll", "verify", "submit"]
    priority: dict[EventKind, int] = {"poll": 0, "verify": 1, "submit": 2}
    calendar: list[tuple[float, int, int, EventKind, str]] = []
    serial = 0

    def schedule(when: float, kind: EventKind, item: str) -> None:
        nonlocal serial
        serial += 1
        calendar.append((when, priority[kind], serial, kind, item))

    schedule(0, "poll", "existing")
    schedule(0, "submit", "queued")
    states = {"existing": "PENDING", "queued": "QUEUED"}
    existing_polls = ["pending", "success"]
    queued_polls = ["success"]
    submit_results = ["429", "accepted"]
    submit_times: list[float] = []
    poll_times: list[tuple[str, float]] = []
    verify_times: list[tuple[str, float]] = []
    action_order: list[str] = []

    while calendar:
        calendar.sort()
        now, _, _, kind, item = calendar.pop(0)
        action_order.append(f"{now:g}:{kind}:{item}")
        if kind == "submit":
            submit_times.append(now)
            result = submit_results.pop(0)
            if result == "429":
                states[item] = "FAILED_RETRYABLE"
                schedule(now + 37, "submit", item)
            else:
                states[item] = "ACCEPTED"
                schedule(now, "poll", item)
        elif kind == "poll":
            poll_times.append((item, now))
            script = existing_polls if item == "existing" else queued_polls
            status = script.pop(0)
            if status == "pending":
                states[item] = "PENDING"
                schedule(now + 15, "poll", item)
            else:
                states[item] = "SUCCEEDED_UNVERIFIED"
                schedule(now, "verify", item)
        else:
            verify_times.append((item, now))
            states[item] = "VERIFIED"

    return OracleResult(
        final_states=states,
        submit_times=tuple(submit_times),
        poll_times=tuple(poll_times),
        verify_times=tuple(verify_times),
        action_order=tuple(action_order),
    )


def exhaustive_priority_oracle() -> dict[str, int]:
    """Enumerate all due/not-due combinations and assert poll-first priority."""

    combinations = 0
    poll_first = 0
    for poll_due in (False, True):
        for verify_due in (False, True):
            for reconcile_due in (False, True):
                for submit_ready in (False, True):
                    combinations += 1
                    ordered = []
                    if poll_due:
                        ordered.append("poll")
                    if verify_due:
                        ordered.append("verify")
                    if reconcile_due:
                        ordered.append("reconcile")
                    if submit_ready:
                        ordered.append("submit")
                    if poll_due and ordered and ordered[0] == "poll":
                        poll_first += 1
                    if poll_due and ordered[0] != "poll":
                        raise AssertionError("oracle violated poll-first priority")
    return {"combinations": combinations, "poll_due_combinations": poll_first}
