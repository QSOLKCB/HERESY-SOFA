#!/usr/bin/env python3
import argparse
import json
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

from corrected import Scheduler, State
from fixtures import CostList, FakeAPI, FakeClock, http_error
from original_loop import SimulationLimit, run_original

SEED = 26051108


def task_summary(tasks):
    return {
        task.url: {
            "state": task.state.value,
            "submit_attempts": task.submit_attempts,
            "poll_errors": task.poll_errors,
            "detail": task.terminal_detail,
            "transitions": task.transitions,
        }
        for task in tasks
    }


def main(receipt_path):
    started = datetime.now(timezone.utc).isoformat()
    checks = []
    evidence = {}

    def check(name, actual, expected, classification="EXECUTED"):
        checks.append({"name": name, "actual": actual, "expected": expected,
                       "passed": actual == expected, "classification": classification})

    api = FakeAPI(
        {"blocked": [http_error(429, 7) for _ in range(10)]},
        {"job-existing": [{"status": "success"}]},
    )
    clock = FakeClock()
    starvation = None
    try:
        run_original(["blocked"], api, clock, max_operations=6,
                     initial_inflight={"job-existing": "existing"})
    except SimulationLimit as exc:
        starvation = {"operations": exc.operations, "queue": exc.queue,
                      "inflight": exc.inflight, "sleeps": clock.sleeps,
                      "submit_count": len(api.submit_calls),
                      "poll_count": len(api.poll_calls)}
    evidence["original_repeated_429"] = starvation
    check("original_repeated_429_hits_bound", starvation is not None, True)
    check("continue_starves_existing_poll", starvation["poll_count"], 0)
    check("retry_after_ignored_for_fixed_900", sorted(set(starvation["sleeps"])), [900.0])
    check("original_has_no_retry_ceiling", starvation["submit_count"], 6)

    api503 = FakeAPI({"blocked": [http_error(503, 2) for _ in range(10)]})
    clock503 = FakeClock()
    repeated503 = False
    try:
        run_original(["blocked"], api503, clock503, max_operations=4)
    except SimulationLimit:
        repeated503 = True
    check("original_repeated_503_also_unbounded", repeated503, True)

    status_results = {}
    for label, statuses in {
        "pending_success": [{"status": "pending"}, {"status": "success"}],
        "error": [{"status": "error", "message": "synthetic"}],
        "unknown": [{"status": "mystery"}],
    }.items():
        api_status = FakeAPI({label: [{"job_id": "job-" + label}]},
                             {"job-" + label: statuses})
        result = run_original([label], api_status, FakeClock(), max_operations=10)
        status_results[label] = result["results"]
    evidence["original_status_results"] = status_results
    check("original_pending_then_success", status_results["pending_success"][0]["status"]["status"],
          "success")
    check("original_records_error_terminal", status_results["error"][0]["status"]["status"], "error")
    check("original_records_unknown_as_terminal", status_results["unknown"][0]["status"]["status"],
          "mystery")

    missing_api = FakeAPI({"missing": [{}]})
    missing_result = run_original(["missing"], missing_api, FakeClock(), max_operations=5)
    check("original_missing_job_id_silently_drops_url", missing_result["results"], [])
    check("original_missing_job_id_submitted_once", len(missing_api.submit_calls), 1)

    poll_error_api = FakeAPI({"poll-error": [{"job_id": "job-poll-error"}]},
                             {"job-poll-error": [http_error(429, 5)]})
    unhandled_poll_code = None
    try:
        run_original(["poll-error"], poll_error_api, FakeClock(), max_operations=5)
    except urllib.error.HTTPError as exc:
        unhandled_poll_code = exc.code
    check("original_poll_429_unhandled", unhandled_poll_code, 429)

    duplicate_api = FakeAPI()
    duplicate_result = run_original(["duplicate", "duplicate"], duplicate_api,
                                    FakeClock(), concurrency=3, max_operations=10)
    check("original_duplicate_submissions", len(duplicate_api.submit_calls), 2)
    check("original_duplicate_results", len(duplicate_result["results"]), 2)

    shift_costs = {}
    for size in (100, 200):
        queue_api = FakeAPI()
        result = run_original([f"u-{i}" for i in range(size)], queue_api, FakeClock(),
                              concurrency=size, max_operations=size * 3,
                              queue_factory=CostList)
        shift_costs[str(size)] = result["queue_shift_cost"]
    evidence["front_list_shift_costs"] = shift_costs
    check("pop0_shift_cost_n100", shift_costs["100"], 100 * 99 // 2)
    check("pop0_shift_cost_n200", shift_costs["200"], 200 * 199 // 2)
    check("doubling_queue_is_quadratic",
          round(shift_costs["200"] / shift_costs["100"], 2), 4.02)

    fair_api = FakeAPI(
        {
            "existing": [{"job_id": "job-existing"}],
            "blocked": [http_error(429, 30), http_error(429, 30), http_error(429, 30)],
        },
        {"job-existing": [{"status": "success"}]},
    )
    fair_clock = FakeClock()
    fair_tasks = Scheduler(fair_api, fair_clock, concurrency=2,
                           max_submit_attempts=3).run(["existing", "blocked"])
    fair = task_summary(fair_tasks)
    evidence["reference_fairness"] = {"tasks": fair, "sleeps": fair_clock.sleeps,
                                      "poll_calls": fair_api.poll_calls}
    check("reference_polls_existing_during_submit_backoff", fair["existing"]["state"], "succeeded")
    check("reference_429_retry_ceiling", fair["blocked"]["detail"], "submit_http_429_ceiling")
    check("reference_existing_poll_count", fair_api.poll_calls.count("job-existing"), 1)

    service_api = FakeAPI({"service": [http_error(503), http_error(503)]})
    service_tasks = Scheduler(service_api, FakeClock(), max_submit_attempts=2).run(["service"])
    check("reference_503_retry_ceiling", service_tasks[0].terminal_detail,
          "submit_http_503_ceiling")

    missing_ref_api = FakeAPI({"missing": [{}, {}]})
    missing_tasks = Scheduler(missing_ref_api, FakeClock(), max_submit_attempts=2).run(["missing"])
    check("reference_missing_job_id_ceiling", missing_tasks[0].terminal_detail,
          "missing_job_id_ceiling")

    pending_api = FakeAPI({"pending": [{"job_id": "job-pending"}]},
                          {"job-pending": [{"status": "pending"}, {"status": "success"}]})
    pending_tasks = Scheduler(pending_api, FakeClock()).run(["pending"])
    check("reference_pending_then_success", pending_tasks[0].state.value, "succeeded")

    error_api = FakeAPI({"error": [{"job_id": "job-error"}]},
                        {"job-error": [{"status": "error"}]})
    error_tasks = Scheduler(error_api, FakeClock()).run(["error"])
    check("reference_error_explicit_failure", error_tasks[0].terminal_detail, "remote_error")

    unknown_api = FakeAPI({"unknown": [{"job_id": "job-unknown"}]},
                          {"job-unknown": [{"status": "mystery"}]})
    unknown_tasks = Scheduler(unknown_api, FakeClock()).run(["unknown"])
    check("reference_unknown_explicit_failure", unknown_tasks[0].terminal_detail,
          "unknown_status")

    poll_retry_api = FakeAPI({"poll-retry": [{"job_id": "job-poll-retry"}]},
                             {"job-poll-retry": [http_error(429, 7), {"status": "success"}]})
    poll_retry_clock = FakeClock()
    poll_retry_tasks = Scheduler(poll_retry_api, poll_retry_clock).run(["poll-retry"])
    check("reference_poll_retry_after_eventually_succeeds",
          poll_retry_tasks[0].state.value, "succeeded")
    check("reference_poll_retry_after_honored",
          7.0 in poll_retry_clock.sleeps, True)

    dedupe_api = FakeAPI()
    dedupe_tasks = Scheduler(dedupe_api, FakeClock()).run(["same", "same"])
    check("reference_deduplicates_input", len(dedupe_tasks), 1)
    check("reference_deduplicates_submissions", len(dedupe_api.submit_calls), 1)

    all_submit_calls = fair_api.submit_calls + service_api.submit_calls + missing_ref_api.submit_calls
    check("reference_always_passes_if_not_archived_within",
          all(call["params"].get("if_not_archived_within") == "30d"
              for call in all_submit_calls), True)

    passed = all(item["passed"] for item in checks)
    receipt = {
        "case": "CASE-08",
        "source_id": "da4cf061-dba9-4c01-b42c-f94e6f3b6279",
        "source_author": "Agent McAgentFace",
        "seed": SEED,
        "started_utc": started,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "command": "uv run --no-project --offline --no-managed-python python test_case_08.py --receipt receipt.json",
        "process_exit_code": 0 if passed else 1,
        "external_services": "none; deterministic fake API and fake clock only",
        "real_sleep_seconds": 0,
        "checks": checks,
        "evidence": evidence,
        "external_claims": {
            "account_shared_budget": "UNSUPPORTED",
            "low_single_digit_concurrency": "UNSUPPORTED",
            "if_not_archived_within_budget_effect": "NOT_TESTED",
            "actual_quota_or_retry_window": "NOT_TESTED"
        },
        "conclusion": {
            "classification": "CONFIRMED_DEFECT",
            "defect": "On repeated submit 429/503, continue stays inside the fill loop and repeatedly retries the front URL, so existing in-flight jobs are never polled. Retry-After, retry ceilings, missing job IDs, poll errors, unknown states, deduplication, and O(1) queue operations are absent.",
            "minimal_correction": "Use deque plus explicit task states/deadlines; poll due work before submits; honor bounded Retry-After-aware retries; treat missing/unknown states explicitly; deduplicate inputs."
        }
    }
    Path(receipt_path).write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"case": "CASE-08", "passed": passed,
                      "checks": len(checks), "real_sleep_seconds": 0}, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", required=True)
    raise SystemExit(main(parser.parse_args().receipt))
