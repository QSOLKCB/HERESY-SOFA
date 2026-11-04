#!/usr/bin/env python3
"""Execute deterministic offline SPN2 adversarial controls and emit JSON."""

from __future__ import annotations

import json
import platform
import random
from typing import Any

from reference_model import exhaustive_priority_oracle, run_oracle
from scheduler_models import (
    AccountQuota,
    AdmissionCoordinator,
    BrokenPostedLoop,
    FairScheduler,
    FakeHTTPError,
    FakeSPN2API,
    PollEvent,
    State,
    SubmitEvent,
    VirtualClock,
    operation_counts,
)


SEED = 26051105
TIMESTAMP = "20261105000000"
REQUIRED_STATES = {state.value for state in State}


class Recorder:
    def __init__(self) -> None:
        self.assertions: list[dict[str, Any]] = []

    def check(
        self,
        test_id: str,
        condition: bool,
        *,
        expected: Any,
        actual: Any,
        negative_control: bool = False,
        evidence_class: str = "EXECUTED_SIMULATED",
    ) -> None:
        item = {
            "test_id": test_id,
            "passed": bool(condition),
            "expected": expected,
            "actual": actual,
            "negative_control": negative_control,
            "evidence_class": evidence_class,
        }
        self.assertions.append(item)
        if not condition:
            raise AssertionError(f"{test_id}: expected {expected!r}, observed {actual!r}")


def actions(result: dict[str, Any], operation: str, task_id: str | None = None) -> list[dict[str, Any]]:
    return [
        action for action in result["actions"]
        if action["operation"] == operation
        and (task_id is None or action["task_id"] == task_id)
    ]


def scenario_broken(record: Recorder) -> dict[str, Any]:
    api = FakeSPN2API(
        submit={"queued": [SubmitEvent("http_429") for _ in range(4)]},
        poll={"existing-job": [PollEvent("pending")]},
    )
    clock = VirtualClock()
    broken = BrokenPostedLoop(api, clock, concurrency=3, backoff=900)
    result = broken.run(
        ["queued"], {"existing-job": "existing"},
        capacity_iteration_ceiling=4,
    )
    record.check("C1-repeated-submits", result["submission_attempts"] == 4, expected=4, actual=result["submission_attempts"], negative_control=True)
    record.check("C1-zero-polls", result["polling_attempts"] == 0, expected=0, actual=result["polling_attempts"], negative_control=True)
    record.check("C1-virtual-backoff", result["virtual_elapsed"] == 3600, expected=3600, actual=result["virtual_elapsed"], negative_control=True)
    record.check(
        "C1-stuck-inside-capacity-loop",
        result["stop_reason"] == "ceiling_inside_capacity_loop",
        expected="ceiling_inside_capacity_loop", actual=result["stop_reason"], negative_control=True,
    )

    # The minimized failing trace uses only one existing job, one URL and two 429s.
    minimal_api = FakeSPN2API(
        submit={"q": [SubmitEvent("http_429"), SubmitEvent("http_429")]},
        poll={"j": [PollEvent("pending")]},
    )
    minimal = BrokenPostedLoop(minimal_api, VirtualClock(), concurrency=2, backoff=1).run(
        ["q"], {"j": "existing"}, capacity_iteration_ceiling=2,
    )
    record.check(
        "C1-minimal-trace", minimal["submission_attempts"] == 2 and minimal["polling_attempts"] == 0,
        expected={"submits": 2, "polls": 0},
        actual={"submits": minimal["submission_attempts"], "polls": minimal["polling_attempts"]},
        negative_control=True,
    )
    result["minimum_counterexample"] = minimal
    result["api_calls"] = api.call_log
    return result


def scenario_fair_and_oracle(record: Recorder) -> dict[str, Any]:
    api = FakeSPN2API(
        submit={
            "https://example.invalid/queued": [
                SubmitEvent("http_429", retry_after=37),
                SubmitEvent("accepted", job_id="queued-job"),
            ]
        },
        poll={
            "existing-job": [PollEvent("pending"), PollEvent("success", TIMESTAMP)],
            "queued-job": [PollEvent("success", TIMESTAMP)],
        },
        lookup={
            "https://example.invalid/existing": [True],
            "https://example.invalid/queued": [True],
        },
    )
    scheduler = FairScheduler(api, VirtualClock(), concurrency=2, max_submit_attempts=3)
    scheduler.add_existing("existing", "https://example.invalid/existing", "existing-job")
    scheduler.add_queued("queued", "https://example.invalid/queued")
    result = scheduler.run()
    submit_times = [item["time"] for item in actions(result, "submit", "queued")]
    poll_pairs = [(item["task_id"], item["time"]) for item in actions(result, "poll")]
    verify_pairs = [(item["task_id"], item["time"]) for item in actions(result, "verify")]
    action_order = tuple(
        f"{item['time']:g}:{item['operation']}:{item['task_id']}"
        for item in result["actions"]
    )
    record.check("C2-poll-first", result["actions"][0]["operation"] == "poll", expected="poll", actual=result["actions"][0], negative_control=False)
    record.check("C2-retry-after", submit_times == [0, 37], expected=[0, 37], actual=submit_times)
    record.check(
        "C2-existing-progress",
        result["tasks"]["existing"]["state"] == State.VERIFIED,
        expected=State.VERIFIED, actual=result["tasks"]["existing"]["state"],
    )
    record.check(
        "C2-queued-progress",
        result["tasks"]["queued"]["state"] == State.VERIFIED,
        expected=State.VERIFIED, actual=result["tasks"]["queued"]["state"],
    )
    record.check("C2-no-step-ceiling", not result["stopped_by_ceiling"], expected=False, actual=result["stopped_by_ceiling"])

    oracle = run_oracle()
    agreement = {
        "final_states": {
            key: result["tasks"][key]["state"] for key in ("existing", "queued")
        } == oracle.final_states,
        "submit_times": tuple(submit_times) == oracle.submit_times,
        "poll_times": tuple(poll_pairs) == oracle.poll_times,
        "verify_times": tuple(verify_pairs) == oracle.verify_times,
        "action_order": action_order == oracle.action_order,
    }
    record.check(
        "C2-independent-oracle", all(agreement.values()),
        expected={key: True for key in agreement}, actual=agreement,
    )
    result["oracle"] = {
        "agreement": agreement,
        "final_states": oracle.final_states,
        "submit_times": list(oracle.submit_times),
        "poll_times": [list(item) for item in oracle.poll_times],
        "verify_times": [list(item) for item in oracle.verify_times],
        "action_order": list(oracle.action_order),
    }
    result["api_calls"] = api.call_log
    return result


def scenario_bounded_refusal(record: Recorder) -> dict[str, Any]:
    api = FakeSPN2API(submit={
        "https://example.invalid/refused": [
            SubmitEvent("http_429", retry_after=5),
            SubmitEvent("http_429", retry_after=5),
            SubmitEvent("http_429", retry_after=5),
        ]
    })
    scheduler = FairScheduler(api, VirtualClock(), max_submit_attempts=3)
    scheduler.add_queued("refused", "https://example.invalid/refused")
    result = scheduler.run()
    task = result["tasks"]["refused"]
    record.check("C2-permanent-refusal-bounded", task["submit_attempts"] == 3, expected=3, actual=task["submit_attempts"])
    record.check("C2-no-eventual-success-claim", task["state"] == State.FAILED_PERMANENT, expected=State.FAILED_PERMANENT, actual=task["state"])
    record.check("C2-bounded-queue", result["max_delayed_length"] <= 1 and result["max_ready_length"] <= 1, expected="both <= 1", actual={"ready": result["max_ready_length"], "delayed": result["max_delayed_length"]})
    result["api_calls"] = api.call_log
    return result


def scenario_lost_acceptance(record: Recorder) -> dict[str, Any]:
    url = "https://example.invalid/lost"
    api = FakeSPN2API(
        submit={url: [SubmitEvent("http_503", job_id="lost-job", server_accepted=True)]},
        reconcile={url: [None, "lost-job"]},
        poll={"lost-job": [PollEvent("success", TIMESTAMP)]},
        lookup={url: [True]},
    )
    scheduler = FairScheduler(api, VirtualClock(), reconcile_interval=5, max_reconcile_attempts=3)
    scheduler.add_queued("lost", url)
    result = scheduler.run()
    task = result["tasks"]["lost"]
    record.check("C3-no-blind-resubmit", task["submit_attempts"] == 1, expected=1, actual=task["submit_attempts"], negative_control=True)
    record.check("C3-reconciled", task["reconcile_attempts"] == 2 and task["state"] == State.VERIFIED, expected={"reconcile": 2, "state": State.VERIFIED}, actual={"reconcile": task["reconcile_attempts"], "state": task["state"]})

    unresolved_url = "https://example.invalid/unresolved"
    unresolved_api = FakeSPN2API(
        submit={unresolved_url: [SubmitEvent("http_503", job_id="ghost-job", server_accepted=True)]},
        reconcile={unresolved_url: [None, None]},
    )
    unresolved = FairScheduler(
        unresolved_api, VirtualClock(), reconcile_interval=5,
        max_reconcile_attempts=2,
    )
    unresolved.add_queued("unresolved", unresolved_url)
    unresolved_result = unresolved.run()
    unresolved_task = unresolved_result["tasks"]["unresolved"]
    record.check(
        "C3-bounded-manual-path",
        unresolved_task["state"] == State.UNCERTAIN_ACCEPTANCE
        and unresolved_task["manual_intervention"]
        and unresolved_task["submit_attempts"] == 1,
        expected={"state": State.UNCERTAIN_ACCEPTANCE, "manual": True, "submits": 1},
        actual={"state": unresolved_task["state"], "manual": unresolved_task["manual_intervention"], "submits": unresolved_task["submit_attempts"]},
    )
    result["api_calls"] = api.call_log
    result["unresolved_control"] = unresolved_result
    result["unresolved_api_calls"] = unresolved_api.call_log
    return result


def scenario_missing_job_id(record: Recorder) -> dict[str, Any]:
    ambiguous_url = "https://example.invalid/missing-ambiguous"
    ambiguous_api = FakeSPN2API(
        submit={ambiguous_url: [SubmitEvent("missing_job_id", body={"status": "pending"})]},
        reconcile={ambiguous_url: [None]},
    )
    ambiguous = FairScheduler(ambiguous_api, VirtualClock(), max_reconcile_attempts=1)
    ambiguous.add_queued("ambiguous", ambiguous_url)
    ambiguous_result = ambiguous.run()
    ambiguous_task = ambiguous_result["tasks"]["ambiguous"]
    history_reasons = [event["reason"] for event in ambiguous_task["history"]]
    record.check(
        "C4-missing-id-ambiguous",
        ambiguous_task["state"] == State.UNCERTAIN_ACCEPTANCE
        and ambiguous_task["manual_intervention"]
        and "protocol_invalid_missing_job_id_acceptance_unknown" in history_reasons,
        expected="protocol-invalid, uncertain, manual",
        actual={"state": ambiguous_task["state"], "manual": ambiguous_task["manual_intervention"], "history": history_reasons},
        negative_control=True,
    )

    rejected_url = "https://example.invalid/missing-rejected"
    rejected_api = FakeSPN2API(submit={
        rejected_url: [SubmitEvent("missing_job_id", body={"status": "error", "accepted": False})]
    })
    rejected = FairScheduler(rejected_api, VirtualClock())
    rejected.add_queued("rejected", rejected_url)
    rejected_result = rejected.run()
    rejected_task = rejected_result["tasks"]["rejected"]
    record.check(
        "C4-explicit-rejection",
        rejected_task["state"] == State.FAILED_PERMANENT and rejected_task["reconcile_attempts"] == 0,
        expected={"state": State.FAILED_PERMANENT, "reconcile": 0},
        actual={"state": rejected_task["state"], "reconcile": rejected_task["reconcile_attempts"]},
    )
    return {
        "ambiguous": ambiguous_result,
        "ambiguous_api_calls": ambiguous_api.call_log,
        "explicit_rejection": rejected_result,
        "explicit_rejection_api_calls": rejected_api.call_log,
    }


def scenario_verification(record: Recorder) -> dict[str, Any]:
    absent_url = "https://example.invalid/index-absent"
    absent_api = FakeSPN2API(
        submit={absent_url: [SubmitEvent("accepted", job_id="absent-job")]},
        poll={"absent-job": [PollEvent("success", TIMESTAMP)]},
        lookup={absent_url: [False, False]},
    )
    absent = FairScheduler(absent_api, VirtualClock(), verify_interval=20, max_verify_attempts=2)
    absent.add_queued("absent", absent_url)
    absent_result = absent.run()
    absent_task = absent_result["tasks"]["absent"]
    record.check(
        "C5-success-not-durable-proof",
        absent_task["state"] == State.SUCCEEDED_UNVERIFIED and absent_task["manual_intervention"],
        expected={"state": State.SUCCEEDED_UNVERIFIED, "manual": True},
        actual={"state": absent_task["state"], "manual": absent_task["manual_intervention"]},
        negative_control=True,
    )

    delayed_url = "https://example.invalid/index-delayed"
    delayed_api = FakeSPN2API(
        submit={delayed_url: [SubmitEvent("accepted", job_id="delayed-job")]},
        poll={"delayed-job": [PollEvent("success", TIMESTAMP)]},
        lookup={delayed_url: [False, True]},
    )
    delayed = FairScheduler(delayed_api, VirtualClock(), verify_interval=20, max_verify_attempts=3)
    delayed.add_queued("delayed", delayed_url)
    delayed_result = delayed.run()
    delayed_task = delayed_result["tasks"]["delayed"]
    record.check(
        "C5-eventual-index",
        delayed_task["state"] == State.VERIFIED and delayed_task["verify_attempts"] == 2,
        expected={"state": State.VERIFIED, "attempts": 2},
        actual={"state": delayed_task["state"], "attempts": delayed_task["verify_attempts"]},
    )
    return {
        "index_absent": absent_result,
        "index_absent_api_calls": absent_api.call_log,
        "delayed_index": delayed_result,
        "delayed_index_api_calls": delayed_api.call_log,
    }


def scenario_unknown_status(record: Recorder) -> dict[str, Any]:
    url = "https://example.invalid/unknown-status"
    api = FakeSPN2API(
        submit={url: [SubmitEvent("accepted", job_id="unknown-job")]},
        poll={"unknown-job": [PollEvent("mystery"), PollEvent("success", TIMESTAMP)]},
        lookup={url: [True]},
    )
    scheduler = FairScheduler(api, VirtualClock(), poll_interval=7, max_poll_attempts=3)
    scheduler.add_queued("unknown", url)
    result = scheduler.run()
    task = result["tasks"]["unknown"]
    history_states = [item["state"] for item in task["history"]]
    record.check(
        "C2-unknown-status-explicit-retry",
        State.FAILED_RETRYABLE in history_states and task["state"] == State.VERIFIED,
        expected={"history_contains": State.FAILED_RETRYABLE, "final": State.VERIFIED},
        actual={"history": history_states, "final": task["state"]},
    )
    result["api_calls"] = api.call_log
    return result


def scenario_shared_account(record: Recorder, rng: random.Random) -> dict[str, Any]:
    uncoordinated = AccountQuota(limit=1)
    job_a = uncoordinated.submit("worker-a", "https://example.invalid/a")
    rejected = []
    for when in (0, 10):
        try:
            uncoordinated.submit("worker-b", "https://example.invalid/b")
        except FakeHTTPError as exc:
            rejected.append({"time": when, "status": exc.status})
    record.check(
        "C6-independent-limits-exceed-account",
        len(rejected) == 2 and uncoordinated.rejections == 2,
        expected=2, actual=uncoordinated.rejections, negative_control=True,
    )

    coordinated_quota = AccountQuota(limit=1)
    coordinator = AdmissionCoordinator(limit=1, lease_seconds=5)
    state_a, token_a = coordinator.acquire("worker-a", "https://example.invalid/a", 0)
    state_b_wait, _ = coordinator.acquire("worker-b", "https://example.invalid/b", 0)
    coordinated_job_a = coordinated_quota.submit("worker-a", "https://example.invalid/a")
    coordinated_quota.finish(coordinated_job_a)
    assert token_a is not None
    coordinator.release(token_a)
    state_b, token_b = coordinator.acquire("worker-b", "https://example.invalid/b", 1)
    coordinated_job_b = coordinated_quota.submit("worker-b", "https://example.invalid/b")
    record.check(
        "C6-coordinated-admission",
        (state_a, state_b_wait, state_b) == ("ACQUIRED", "WAIT", "ACQUIRED")
        and coordinated_quota.rejections == 0,
        expected=["ACQUIRED", "WAIT", "ACQUIRED", 0],
        actual=[state_a, state_b_wait, state_b, coordinated_quota.rejections],
    )

    crash_coordinator = AdmissionCoordinator(limit=1, lease_seconds=5)
    crash_state, _ = crash_coordinator.acquire("crashed-worker", "https://example.invalid/crash", 0)
    before_expiry, _ = crash_coordinator.acquire("survivor", "https://example.invalid/survive", 1)
    after_expiry, recovered_token = crash_coordinator.acquire("survivor", "https://example.invalid/survive", 6)
    record.check(
        "C6-partial-worker-failure-lease",
        (crash_state, before_expiry, after_expiry) == ("ACQUIRED", "WAIT", "ACQUIRED")
        and recovered_token is not None,
        expected=["ACQUIRED", "WAIT", "ACQUIRED"],
        actual=[crash_state, before_expiry, after_expiry],
    )

    duplicate_coordinator = AdmissionCoordinator(limit=2, lease_seconds=30)
    inputs = [
        "https://example.invalid/dup", "https://example.invalid/b",
        "https://example.invalid/dup", "https://example.invalid/c",
    ]
    rng.shuffle(inputs)
    dispositions = []
    tokens = []
    for index, url in enumerate(inputs):
        disposition, token = duplicate_coordinator.acquire(f"worker-{index}", url, 0)
        dispositions.append({"url": url, "disposition": disposition})
        if token:
            tokens.append(token)
            duplicate_coordinator.release(token, retain_url=True)
    dup_dispositions = [item["disposition"] for item in dispositions if item["url"].endswith("/dup")]
    record.check(
        "C6-duplicate-input-suppression",
        sorted(dup_dispositions) == ["ACQUIRED", "DUPLICATE"],
        expected=["ACQUIRED", "DUPLICATE"], actual=sorted(dup_dispositions),
    )
    return {
        "model_boundary": "Synthetic shared quota; not evidence of Internet Archive limits.",
        "uncoordinated": {
            "first_job": job_a,
            "retry_collisions": rejected,
            "account_rejections": uncoordinated.rejections,
            "local_limits": {"worker-a": 1, "worker-b": 1},
            "synthetic_account_limit": 1,
        },
        "coordinated": {
            "states": [state_a, state_b_wait, state_b],
            "second_token_present": token_b is not None,
            "second_job": coordinated_job_b,
            "account_rejections": coordinated_quota.rejections,
        },
        "partial_failure": {
            "states": [crash_state, before_expiry, after_expiry],
            "lease_recovered": recovered_token is not None,
        },
        "seeded_duplicate_fixture": {
            "seed": SEED, "order": inputs, "dispositions": dispositions,
        },
    }


def scenario_performance(record: Recorder) -> list[dict[str, int]]:
    rows = [operation_counts(size) for size in (8, 32, 128, 512)]
    for row in rows:
        n = row["backlog"]
        record.check(
            f"C7-list-shifts-{n}",
            row["list_element_shifts"] == n * (n - 1) // 2,
            expected=n * (n - 1) // 2, actual=row["list_element_shifts"],
            negative_control=True,
        )
        record.check(
            f"C7-deque-operations-{n}",
            row["deque_front_operations"] == n and row["deque_element_shifts"] == 0,
            expected={"operations": n, "shifts": 0},
            actual={"operations": row["deque_front_operations"], "shifts": row["deque_element_shifts"]},
        )
        record.check(
            f"C7-deadline-count-{n}",
            row["fixed_tick_deadline_checks"] == n * n
            and row["heap_pushes_plus_pops"] == 2 * n,
            expected={"fixed_checks": n * n, "heap_ops": 2 * n},
            actual={"fixed_checks": row["fixed_tick_deadline_checks"], "heap_ops": row["heap_pushes_plus_pops"]},
        )
    record.check(
        "C7-not-wall-clock-only",
        rows[-1]["list_element_shifts"] > rows[-1]["heap_comparisons"]
        and rows[-1]["fixed_tick_deadline_checks"] > rows[-1]["heap_comparisons"],
        expected="instrumented quadratic counts exceed heap comparisons",
        actual=rows[-1],
    )
    return rows


def gather_states(value: Any) -> set[str]:
    states: set[str] = set()
    if isinstance(value, dict):
        if value.get("state") in REQUIRED_STATES:
            states.add(value["state"])
        for child in value.values():
            states.update(gather_states(child))
    elif isinstance(value, list):
        for child in value:
            states.update(gather_states(child))
    return states


def main() -> int:
    rng = random.Random(SEED)
    record = Recorder()
    scenarios: dict[str, Any] = {}
    scenarios["C1_broken_posted_loop"] = scenario_broken(record)
    scenarios["C2_fair_scheduler_and_oracle"] = scenario_fair_and_oracle(record)
    scenarios["C2_permanent_refusal"] = scenario_bounded_refusal(record)
    scenarios["C3_lost_acceptance"] = scenario_lost_acceptance(record)
    scenarios["C4_missing_job_id"] = scenario_missing_job_id(record)
    scenarios["C5_capture_verification"] = scenario_verification(record)
    scenarios["C2_unknown_status"] = scenario_unknown_status(record)
    scenarios["C6_shared_account"] = scenario_shared_account(record, rng)
    scenarios["C7_operation_counts"] = scenario_performance(record)
    scenarios["exhaustive_priority_oracle"] = exhaustive_priority_oracle()

    represented_states = gather_states(scenarios)
    record.check(
        "C-all-required-states-represented",
        represented_states == REQUIRED_STATES,
        expected=sorted(REQUIRED_STATES), actual=sorted(represented_states),
    )
    record.check(
        "C-exhaustive-small-state-space",
        scenarios["exhaustive_priority_oracle"] == {"combinations": 16, "poll_due_combinations": 8},
        expected={"combinations": 16, "poll_due_combinations": 8},
        actual=scenarios["exhaustive_priority_oracle"],
    )

    output = {
        "schema_version": "1.0",
        "campaign": "LOCAL-VERIFY-001",
        "experiment": "SPN2-SCHEDULER",
        "seed": SEED,
        "python": platform.python_version(),
        "network_access": False,
        "real_sleep": False,
        "live_service_claims": False,
        "assertion_count": len(record.assertions),
        "failed_assertion_count": sum(not item["passed"] for item in record.assertions),
        "negative_control_count": sum(item["negative_control"] for item in record.assertions),
        "assertions": record.assertions,
        "represented_states": sorted(represented_states),
        "scenarios": scenarios,
        "limitations": [
            "The fake API does not establish Internet Archive quotas, account limits, retry windows, or idempotency.",
            "A synthetic index lookup models verification logic but is not a live CDX/archive-index query.",
            "The shared-account model demonstrates coordination properties only under its declared synthetic quota.",
        ],
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
