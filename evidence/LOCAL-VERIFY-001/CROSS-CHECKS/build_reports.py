#!/usr/bin/env python3
"""Build the LOCAL-VERIFY-001 reports from executed receipts."""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import io
import json
from pathlib import Path
import subprocess
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "REPORTS"
REPO = Path("/home/trent/HERESY-SOFA")
POSTS = {
    "A": "0b3591f6-75de-4661-a7a7-ec28193e1518",
    "B": "fa8ac823-1616-4df3-9f73-feaa8b5b4bf7",
    "C": "da4cf061-dba9-4c01-b42c-f94e6f3b6279",
}
AUTHORS = {"A": "midhun-hermes", "B": "midhun-hermes", "C": "Agent McAgentFace"}


def utc_now() -> str:
    return dt.datetime.now(dt.UTC).isoformat().replace("+00:00", "Z")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=REPO, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True,
    )
    return result.stdout.strip()


def ancestor(commit: str) -> bool:
    return subprocess.run(
        ["git", "merge-base", "--is-ancestor", commit, "origin/main"],
        cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    ).returncode == 0


def matrix_row(
    test_id: str,
    investigation: str,
    claim: str,
    fixture: str,
    expected: str,
    actual: str,
    negative: bool,
    status: str,
    evidence: str,
    source: str,
    limitations: str,
) -> dict[str, str]:
    return {
        "test_id": test_id,
        "investigation": investigation,
        "original_claim": claim,
        "fixture": fixture,
        "expected_behaviour": expected,
        "actual_result": actual,
        "negative_control": "yes" if negative else "no",
        "pass_fail": status,
        "evidence_class": evidence,
        "evidence_reference": source,
        "limitations": limitations,
    }


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    if not rows:
        raise ValueError(f"no rows for {path}")
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    path.write_text(buffer.getvalue(), encoding="utf-8", newline="")


def main() -> int:
    created = utc_now()
    environment_path = REPORTS / "LOCAL-VERIFY-001-ENVIRONMENT.json"
    execution_path = ROOT / "RECEIPTS" / "LOCAL-VERIFY-001-EXECUTION.json"
    runtime_path = ROOT / "PYTHON-TYPING" / "runtime-result.json"
    scheduler_path = ROOT / "SPN2-SCHEDULER" / "scheduler-result.json"
    checker_path = ROOT / "CROSS-CHECKS" / "checker-inventory.json"
    source_snapshot_path = ROOT / "CROSS-CHECKS" / "current-sofa-source-snapshot.json"

    env = read_json(environment_path)
    execution = read_json(execution_path)
    runtime = read_json(runtime_path)
    scheduler = read_json(scheduler_path)
    checker = read_json(checker_path)
    snapshot = read_json(source_snapshot_path)

    assert env["repository"]["origin_main"] == "59b619d5b09e7966f1ceae1dd9ab14313e3ad20a"
    assert env["repository"]["pr16_is_ancestor_of_origin_main"] is True
    assert env["repository"]["pr17_is_ancestor_of_origin_main"] is True
    assert runtime["failed_assertion_count"] == 0 and runtime["assertion_count"] == 18
    assert scheduler["failed_assertion_count"] == 0 and scheduler["assertion_count"] == 41
    assert execution["total_runtime_assertion_count"] == 59
    assert execution["total_runtime_negative_control_count"] == 20
    assert checker["executables"]["pyright"] is None
    assert checker["executables"]["basedpyright"] is None
    assert checker["bounded_cache_search"]["matches"] == []

    source_identities: dict[str, Any] = {}
    for entry in snapshot["posts"]:
        data = entry["response"]["data"]
        source_identities[data["id"]] = {
            "post_id": data["id"],
            "title": data["title"],
            "author": data["agent_name"],
            "body_sha256": hashlib.sha256(data["body"].encode("utf-8")).hexdigest(),
            "updated_at": data["updated_at"],
            "replies": [
                {
                    "id": reply["id"],
                    "author": reply["agent_name"],
                    "body_sha256": hashlib.sha256(reply["body"].encode("utf-8")).hexdigest(),
                }
                for reply in data["replies"]
            ],
        }

    historical = {
        "schema_version": "1.0",
        "campaign": "LOCAL-VERIFY-001",
        "recorded_at_utc": created,
        "origin_main": git("rev-parse", "origin/main"),
        "required_merges": {
            "pr_16": {
                "commit": "22083e28949d5691731f8cf16ed80fae23899980",
                "ancestor_of_origin_main": ancestor("22083e28949d5691731f8cf16ed80fae23899980"),
            },
            "pr_17": {
                "commit": "59b619d5b09e7966f1ceae1dd9ab14313e3ad20a",
                "ancestor_of_origin_main": ancestor("59b619d5b09e7966f1ceae1dd9ab14313e3ad20a"),
            },
        },
        "frozen_historical_evidence": {
            "codex_primary_report": {
                "path": "evidence/SOFA-HOT-008/WITNESSES/CODEX-001-primary/CODEX-001-REPORT.json",
                "sha256": sha256(REPO / "evidence/SOFA-HOT-008/WITNESSES/CODEX-001-primary/CODEX-001-REPORT.json"),
            },
            "monica_archive": {
                "path": "evidence/SOFA-HOT-008/WITNESSES/MONICA-001/SOFA-HOT-008-MONICA-001-evidence.gz",
                "sha256": sha256(REPO / "evidence/SOFA-HOT-008/WITNESSES/MONICA-001/SOFA-HOT-008-MONICA-001-evidence.gz"),
            },
            "dual_witness_report": {
                "path": "evidence/SOFA-HOT-008/RECONCILIATION/SOFA-HOT-008-DUAL-WITNESS-REPORT.json",
                "sha256": sha256(REPO / "evidence/SOFA-HOT-008/RECONCILIATION/SOFA-HOT-008-DUAL-WITNESS-REPORT.json"),
            },
            "claim_ledger": {
                "path": "evidence/SOFA-HOT-008/RECONCILIATION/SOFA-HOT-008-CLAIM-LEDGER.csv",
                "sha256": sha256(REPO / "evidence/SOFA-HOT-008/RECONCILIATION/SOFA-HOT-008-CLAIM-LEDGER.csv"),
            },
        },
        "current_source_identities": source_identities,
        "preservation_statement": "Historical evidence was read and hashed only; this campaign writes exclusively under LOCAL-VALIDATION and its new archive collection.",
    }
    assert historical["frozen_historical_evidence"]["codex_primary_report"]["sha256"] == "3cebb8b7fff60a5344e91f02c531dcbfe23455a83b518630acdc7c007ec33229"
    assert historical["frozen_historical_evidence"]["monica_archive"]["sha256"] == "cc3d4ae960c6c5afb91ba5d9b3b4be1aae90a49d185931a65d41e858e7e28202"
    write_json(ROOT / "CROSS-CHECKS" / "historical-baseline.json", historical)

    matrix = [
        matrix_row("A1", "GenericAlias", "The reply's GenericAlias[...] code runs on Python 3.11+.", "verbatim reply source", "Construct or produce the claimed output.", "Exit 1; TypeError: type 'types.GenericAlias' is not subscriptable.", True, "PASS", "EXECUTED_NATIVE", "PYTHON-TYPING/generic-alias-verbatim.stderr.txt", "CPython 3.14.4 only in this campaign."),
        matrix_row("A2.1", "GenericAlias", "GenericAlias is created by subscription.", "GenericAlias(tuple, (int, Ellipsis))", "Actual API constructs alias with tuple origin.", "Constructed types.GenericAlias; repr tuple[int, ...].", False, "PASS", "EXECUTED_NATIVE", "PYTHON-TYPING/runtime-result.json#A2", "Runtime metadata only."),
        matrix_row("A2.2", "GenericAlias", "Alias metadata enforces element types.", "alias((1, 'not-an-int'))", "Negative control should expose absent enforcement.", "Returned (1, 'not-an-int') unchanged.", True, "PASS", "EXECUTED_NATIVE", "PYTHON-TYPING/runtime-result.json#A2-no-runtime-enforcement", "Does not address static analysis."),
        matrix_row("A3.1", "TypeVarTuple", "A valid variadic generic accepts a sequence of types.", "Packed[int], Packed[int,str], Packed[int,int,int]", "All runtime subscriptions accepted.", "All accepted; get_args preserved each sequence.", False, "PASS", "EXECUTED_NATIVE", "PYTHON-TYPING/runtime-result.json#typevartuple_runtime_forms", "CPython runtime only."),
        matrix_row("A3.2", "TypeVarTuple", "A literal ellipsis is rejected by the runtime pack.", "Packed[int, ...] and Packed[...]", "Counterexample should be accepted if runtime is metadata-permissive.", "Both accepted; args contain Ellipsis.", True, "PASS", "CONTRADICTED", "PYTHON-TYPING/runtime-result.json#A3-literal-ellipsis", "Does not predict Pyright."),
        matrix_row("A5.1", "GenericAlias", "An ordinary one-TypeVar generic accepts two arguments.", "Single[int, str]", "Raise for excess arguments.", "TypeError: actual 2, expected 1.", True, "PASS", "EXECUTED_NATIVE", "PYTHON-TYPING/runtime-result.json#single_too_many_args", "Custom hooks can change runtime behavior."),
        matrix_row("A5.2", "GenericAlias", "A custom __class_getitem__ automatically provides typing metadata.", "RuntimeOnly[int, ...]", "Hook runs but result has no typing origin.", "Hook returned a tuple; get_origin is None.", True, "PASS", "EXECUTED_NATIVE", "PYTHON-TYPING/runtime-result.json#custom_class_getitem", "Static checkers are separate."),
        matrix_row("A4.1", "Static typing", "Plain TypeVarTuple use is recognized.", "mypy strict positive fixture", "No diagnostics.", "mypy 1.19.1 exit 0.", False, "PASS", "EXECUTED_NATIVE", "PYTHON-TYPING/A4-genericalias-positive.txt", "Version-scoped to mypy 1.19.1."),
        matrix_row("A4.2", "Static typing", "Literal ellipsis in a user pack is accepted by the checker.", "Packed[int, ...]", "Record installed checker behavior.", "mypy 1.19.1: Unexpected '...' [misc].", True, "PASS", "EXECUTED_NATIVE", "PYTHON-TYPING/A4-genericalias-negative.txt", "Mypy is not Pyright."),
        matrix_row("A4.3", "Static typing", "Runtime custom subscription is a useful static generic.", "RuntimeOnly[int, ...]", "Record installed checker behavior.", "mypy: type is not generic and not indexable.", True, "PASS", "EXECUTED_NATIVE", "PYTHON-TYPING/A4-genericalias-negative.txt", "Mypy 1.19.1 only."),
        matrix_row("A4.4", "Static typing", "Pyright 1.1.414 reports the documented diagnostics.", "exact Pyright version", "Execute exact version.", "Executable and verified local cache absent.", False, "NOT_TESTED", "NOT_TESTED", "CROSS-CHECKS/checker-inventory.json", "No installation or npm permitted."),
        matrix_row("A4.5", "Static typing", "Mypy 2.3.1 has the reported behavior.", "exact mypy version", "Execute exact version.", "Executable and verified local cache absent.", False, "NOT_TESTED", "NOT_TESTED", "CROSS-CHECKS/checker-inventory.json", "No installation permitted."),
        matrix_row("B1", "Dataclass", "myclass[C]() constructs a C default.", "myclass[C]()", "var exact type C.", "var exact type C.", False, "PASS", "EXECUTED_NATIVE", "PYTHON-TYPING/runtime-result.json#posted_dataclass_defaults", "None."),
        matrix_row("B2", "Dataclass", "The ignored default is valid for myclass[C2]().", "myclass[C2]()", "Negative control should expose invariant violation.", "var exact type C, not C2.", True, "PASS", "CONTRADICTED", "PYTHON-TYPING/runtime-result.json#B-default-C2-violates-parameter", "Runtime parameter metadata is erased."),
        matrix_row("B3", "Dataclass", "A concrete subclass override can provide C2.", "myclass_child()", "var exact type C2.", "var exact type C2.", False, "PASS", "EXECUTED_NATIVE", "PYTHON-TYPING/runtime-result.json#B-child-override", "Requires annotation and factory override."),
        matrix_row("B4", "Dataclass", "# type: ignore repairs runtime correctness.", "ignored factory plus reveal_type", "Checker may be silent while runtime remains wrong.", "mypy exit 0 reveals C2; native runtime constructs C.", True, "PASS", "CONTRADICTED", "PYTHON-TYPING/B-mypy-ignore-unsound.txt; runtime-result.json", "Checker silence is not runtime enforcement."),
        matrix_row("B5", "Dataclass", "Required field is sound.", "RequiredField[C2](C2())", "Runtime C2 and mypy strict pass.", "Runtime C2; mypy 1.19.1 exit 0.", False, "PASS", "EXECUTED_NATIVE", "PYTHON-TYPING/runtime-result.json; B-mypy-sound-designs.txt", "Mypy 1.19.1."),
        matrix_row("B6", "Dataclass", "Caller factory is sound.", "CallerFactory[C2](C2)", "Runtime C2 and mypy strict pass.", "Runtime C2; mypy 1.19.1 exit 0.", False, "PASS", "EXECUTED_NATIVE", "PYTHON-TYPING/runtime-result.json; B-mypy-sound-designs.txt", "Mypy 1.19.1."),
        matrix_row("B7", "Dataclass", "Concrete override is sound.", "ConcreteChild()", "Runtime C2 and mypy strict pass.", "Runtime C2; mypy 1.19.1 exit 0.", False, "PASS", "EXECUTED_NATIVE", "PYTHON-TYPING/runtime-result.json; B-mypy-sound-designs.txt", "Mypy 1.19.1."),
        matrix_row("B8", "Dataclass", "The unsuppressed base factory is assignable to CT.", "dataclass mismatch fixture", "Mypy should report C versus CT mismatch.", "mypy 1.19.1 exit 1 [assignment].", True, "PASS", "EXECUTED_NATIVE", "PYTHON-TYPING/B-mypy-mismatch.txt", "Mypy 1.19.1."),
        matrix_row("C1.1", "SPN2", "Repeated requeue/continue still allows polling.", "1 in-flight + 1 queued + four 429s", "Expose starvation before outer poll block.", "4 submits, 0 polls, 3600 virtual seconds.", True, "PASS", "EXECUTED_SIMULATED", "SPN2-SCHEDULER/scheduler-result.json#C1_broken_posted_loop", "Control flow only; not a live service test."),
        matrix_row("C1.2", "SPN2", "Starvation needs a large workload.", "1 in-flight + 1 queued + two 429s", "Minimize failing trace.", "2 submits, 0 polls.", True, "PASS", "EXECUTED_SIMULATED", "SPN2-SCHEDULER/scheduler-result.json#minimum_counterexample", "Artificial ceiling bounds the intentionally broken loop."),
        matrix_row("C2.1", "SPN2", "Poll-first deadlines prevent this starvation.", "existing pending/success + queued 429/accepted", "Poll at t=0 before submit; both progress.", "First action poll; both tasks VERIFIED in fake model.", False, "PASS", "EXECUTED_SIMULATED", "SPN2-SCHEDULER/scheduler-result.json#C2_fair_scheduler_and_oracle", "No live eventual-success claim."),
        matrix_row("C2.2", "SPN2", "Fixed 900 seconds should override response guidance.", "429 Retry-After=37", "Use response deadline.", "Submits at virtual t=0 and t=37.", False, "PASS", "EXECUTED_SIMULATED", "SPN2-SCHEDULER/scheduler-result.json#C2-retry-after", "Actual IA header behavior untested."),
        matrix_row("C2.3", "SPN2", "Permanent refusal eventually succeeds.", "three 429s, retry ceiling 3", "Bound attempts without claiming success.", "3 attempts then FAILED_PERMANENT; queue bounds <=1.", True, "PASS", "EXECUTED_SIMULATED", "SPN2-SCHEDULER/scheduler-result.json#C2_permanent_refusal", "Synthetic refusal."),
        matrix_row("C2.4", "SPN2", "Unknown status can be treated as completed.", "mystery then success", "Retry poll explicitly.", "FAILED_RETRYABLE appears, then VERIFIED after success+lookup.", True, "PASS", "EXECUTED_SIMULATED", "SPN2-SCHEDULER/scheduler-result.json#C2_unknown_status", "Synthetic protocol."),
        matrix_row("C3.1", "SPN2", "A 503 submission is safe to blindly resubmit.", "server accepts but response is 503/lost", "Do not resubmit before reconciliation.", "1 submit, 2 reconciliations, recovered job, VERIFIED.", True, "PASS", "EXECUTED_SIMULATED", "SPN2-SCHEDULER/scheduler-result.json#C3_lost_acceptance", "Does not prove IA can reconcile by URL."),
        matrix_row("C3.2", "SPN2", "Unresolved acceptance can retry forever.", "503 plus two empty reconciliations", "Bound and retain uncertainty.", "UNCERTAIN_ACCEPTANCE + manual intervention; 1 submit.", True, "PASS", "EXECUTED_SIMULATED", "SPN2-SCHEDULER/scheduler-result.json#unresolved_control", "Manual policy required."),
        matrix_row("C4.1", "SPN2", "HTTP success without job_id is ordinary success.", "200-like pending body without job_id", "Mark protocol-invalid and acceptance-ambiguous.", "UNCERTAIN_ACCEPTANCE after bounded reconciliation.", True, "PASS", "EXECUTED_SIMULATED", "SPN2-SCHEDULER/scheduler-result.json#C4_missing_job_id", "Live schema unverified."),
        matrix_row("C4.2", "SPN2", "Explicit rejection without job_id is acceptance-ambiguous.", "body status=error accepted=false", "Separate explicit rejection.", "FAILED_PERMANENT, zero reconciliation.", False, "PASS", "EXECUTED_SIMULATED", "SPN2-SCHEDULER/scheduler-result.json#explicit_rejection", "Synthetic body semantics."),
        matrix_row("C5.1", "SPN2", "status=success proves a durable capture.", "success timestamp + two absent index lookups", "Retain unverified state.", "SUCCEEDED_UNVERIFIED + manual intervention.", True, "PASS", "EXECUTED_SIMULATED", "SPN2-SCHEDULER/scheduler-result.json#index_absent", "No live index contacted."),
        matrix_row("C5.2", "SPN2", "Delayed index visibility can be retried.", "absent then present lookup", "Remain unverified, then verify.", "VERIFIED on second lookup at t=20.", False, "PASS", "EXECUTED_SIMULATED", "SPN2-SCHEDULER/scheduler-result.json#delayed_index", "Synthetic eventual consistency."),
        matrix_row("C6.1", "SPN2", "Two independent local caps enforce an account cap.", "two workers local=1, account=1", "Expose aggregate collision.", "Second worker received two synthetic 429s.", True, "PASS", "EXECUTED_SIMULATED", "SPN2-SCHEDULER/scheduler-result.json#uncoordinated", "Synthetic account model only."),
        matrix_row("C6.2", "SPN2", "Shared admission can prevent modeled collisions.", "lease coordinator limit=1", "Serialize admission.", "WAIT then ACQUIRED; zero account rejections.", False, "PASS", "EXECUTED_SIMULATED", "SPN2-SCHEDULER/scheduler-result.json#coordinated", "Not proof of real account limit."),
        matrix_row("C6.3", "SPN2", "Worker failure must strand capacity.", "5-second lease, crashed worker", "Recover after lease expiry.", "WAIT at t=1, ACQUIRED at t=6.", True, "PASS", "EXECUTED_SIMULATED", "SPN2-SCHEDULER/scheduler-result.json#partial_failure", "Lease timing is a design choice."),
        matrix_row("C6.4", "SPN2", "Duplicate URLs need no shared suppression.", "seeded duplicated input", "Admit first, suppress second.", "ACQUIRED then DUPLICATE.", True, "PASS", "EXECUTED_SIMULATED", "SPN2-SCHEDULER/scheduler-result.json#seeded_duplicate_fixture", "Synthetic coordinator."),
        matrix_row("C7.1", "SPN2", "list pop(0) scales like deque popleft.", "backlogs 8,32,128,512", "Count element shifts.", "At n=512 list shifted 130816 elements; deque shifted 0.", True, "PASS", "EXECUTED_SIMULATED", "SPN2-SCHEDULER/scheduler-result.json#C7_operation_counts", "Operation counts, not wall-clock timings."),
        matrix_row("C7.2", "SPN2", "Fixed-tick full scans are equivalent to deadline scheduling.", "n deadlines across n ticks", "Count checks versus heap operations/comparisons.", "n=512: 262144 checks vs 1024 heap push/pop and 7443 comparisons.", True, "PASS", "EXECUTED_SIMULATED", "SPN2-SCHEDULER/scheduler-result.json#C7_operation_counts", "Adversarial deterministic fixture."),
        matrix_row("X1", "Cross-check", "Reference agreement can be inferred from one implementation.", "independent sorted-list oracle", "Compare actions, states and times.", "All five dimensions agree.", False, "PASS", "EXECUTED_SIMULATED", "SPN2-SCHEDULER/scheduler-result.json#oracle", "Agreement is fixture-scoped."),
        matrix_row("X2", "Cross-check", "One process run is reproducible evidence.", "two fresh runs per runtime suite", "Byte-identical outputs.", "Both pairs byte-identical; source hashes unchanged.", False, "PASS", "EXECUTED_NATIVE", "CROSS-CHECKS/determinism.json", "Same workstation/interpreter."),
    ]
    matrix_path = REPORTS / "LOCAL-VERIFY-001-TEST-MATRIX.csv"
    write_csv(matrix_path, matrix)

    claims = [
        {
            "claim_id": "A-01", "case_id": "06", "post_id": POSTS["A"], "original_author": "Milo Humanizer (reply)",
            "exact_sofa_claim": "typing.GenericAlias[tuple[int, ...]] works on Python 3.11+ and supports the shown class declaration.",
            "prior_witness_evidence": "Codex executed failure; Monica did not test the reply.",
            "new_local_evidence": "Verbatim CPython 3.14.4 exit 1 before class declaration.",
            "agreement_or_contradiction": "Agrees with prior Codex; upgrades local version-pinned reproduction.",
            "final_classification": "CONTRADICTED", "evidence_class": "EXECUTED_NATIVE",
            "minimum_counterexample": "from typing import GenericAlias; GenericAlias[tuple[int, ...]]",
            "correction": "Call types.GenericAlias(origin, args); do not claim it enforces types or checker support.",
            "limitations": "Pyright 1.1.414 not run.",
        },
        {
            "claim_id": "A-02", "case_id": "06", "post_id": POSTS["A"], "original_author": AUTHORS["A"],
            "exact_sofa_claim": "Every TypeVarTuple element must be a type, so literal ellipsis is rejected before runtime initialization.",
            "prior_witness_evidence": "Reconciliation found CPython accepted Fixed[int, ...].",
            "new_local_evidence": "Packed[int, ...] and Packed[...] accepted on CPython 3.14.4.",
            "agreement_or_contradiction": "Confirms runtime counterexample; mypy 1.19.1 separately rejects the form.",
            "final_classification": "PARTIALLY_CORRECT", "evidence_class": "EXECUTED_NATIVE",
            "minimum_counterexample": "class Packed(Generic[*Ts]): ...; Packed[int, ...]",
            "correction": "Scope prohibition to the named static checker/version; CPython accepts metadata.",
            "limitations": "Pyright unavailable.",
        },
        {
            "claim_id": "A-03", "case_id": "06", "post_id": POSTS["A"], "original_author": AUTHORS["A"],
            "exact_sofa_claim": "Pyright 1.1.414 emits the stated diagnostics for user generics and custom aliases.",
            "prior_witness_evidence": "Neither archived witness ran Pyright.",
            "new_local_evidence": "No executable or verified cache; not installed.",
            "agreement_or_contradiction": "Still unresolved.",
            "final_classification": "NOT_TESTED", "evidence_class": "NOT_TESTED",
            "minimum_counterexample": "None; prerequisite absent.",
            "correction": "Run the exact fixture under Pyright 1.1.414.",
            "limitations": "Mypy results cannot substitute.",
        },
        {
            "claim_id": "B-01", "case_id": "03", "post_id": POSTS["B"], "original_author": AUTHORS["B"],
            "exact_sofa_claim": "A lambda plus targeted ignore is an acceptable default for arbitrary CT bound to C.",
            "prior_witness_evidence": "Both witnesses found C under C2 specialization.",
            "new_local_evidence": "type(myclass[C2]().var) is C on CPython 3.14.4.",
            "agreement_or_contradiction": "Confirms both witnesses.",
            "final_classification": "CONTRADICTED", "evidence_class": "EXECUTED_NATIVE",
            "minimum_counterexample": "myclass[C2]().var",
            "correction": "Make var required, require Callable[[], CT], or override factory in a concrete subclass.",
            "limitations": "Runtime generic parameters are not enforced automatically.",
        },
        {
            "claim_id": "B-02", "case_id": "03", "post_id": POSTS["B"], "original_author": AUTHORS["B"],
            "exact_sofa_claim": "The targeted ignore repairs the generic default mismatch.",
            "prior_witness_evidence": "Both witnesses classified the ignore as suppression only.",
            "new_local_evidence": "mypy reveals C2 and exits 0 while the runtime fixture constructs C.",
            "agreement_or_contradiction": "Confirms the checker/runtime disagreement.",
            "final_classification": "CONTRADICTED", "evidence_class": "EXECUTED_NATIVE",
            "minimum_counterexample": "declared: MyClass[C2] = MyClass[C2](); reveal_type(declared.var)",
            "correction": "Use a sound API, not an unjustified ignore.",
            "limitations": "Mypy version 1.19.1.",
        },
        {
            "claim_id": "B-03", "case_id": "03", "post_id": POSTS["B"], "original_author": AUTHORS["B"],
            "exact_sofa_claim": "Required-field, caller-factory and concrete override designs preserve CT.",
            "prior_witness_evidence": "Archived Codex ran required/factory alternatives; Monica ran runtime controls.",
            "new_local_evidence": "All three construct C2 and pass mypy 1.19.1 --strict.",
            "agreement_or_contradiction": "Agrees with prior correction.",
            "final_classification": "CONFIRMED", "evidence_class": "EXECUTED_NATIVE",
            "minimum_counterexample": "RequiredField[C2](C2())",
            "correction": "RequiredField is the smallest sound implementation.",
            "limitations": "Exact mypy 2.3.1 not run.",
        },
        {
            "claim_id": "B-04", "case_id": "03", "post_id": POSTS["B"], "original_author": "Nincompoop (reply)",
            "exact_sofa_claim": "The reported mypy 2.3.1 annotation behavior is established locally.",
            "prior_witness_evidence": "Historical users reported it; neither archived witness had 2.3.1.",
            "new_local_evidence": "2.3.1 absent from executable path, uv tools and bounded local caches.",
            "agreement_or_contradiction": "Still unresolved in this campaign.",
            "final_classification": "NOT_TESTED", "evidence_class": "NOT_TESTED",
            "minimum_counterexample": "None; exact version absent.",
            "correction": "Retain version scope and rerun under 2.3.1 when available.",
            "limitations": "1.19.1 cannot substitute for 2.3.1.",
        },
        {
            "claim_id": "C-01", "case_id": "08", "post_id": POSTS["C"], "original_author": AUTHORS["C"],
            "exact_sofa_claim": "The inner requeue/sleep/continue loop safely coexists with polling.",
            "prior_witness_evidence": "Codex reproduced starvation; Monica did not run the exact loop.",
            "new_local_evidence": "Minimum bounded trace: 1 in-flight, 1 queued, two 429s => 2 submits, 0 polls.",
            "agreement_or_contradiction": "Confirms prior single-witness control-flow defect.",
            "final_classification": "CONFIRMED_DEFECT", "evidence_class": "EXECUTED_SIMULATED",
            "minimum_counterexample": "existing={j}; queue=[u]; submit(u)->429 twice",
            "correction": "Poll due work first; place retries on independent deadlines outside the fill loop.",
            "limitations": "No live SPN2 requests.",
        },
        {
            "claim_id": "C-02", "case_id": "08", "post_id": POSTS["C"], "original_author": AUTHORS["C"],
            "exact_sofa_claim": "list pop(0)/insert(0) is suitable scalable queue management.",
            "prior_witness_evidence": "Codex shift counter; Monica proposed deque.",
            "new_local_evidence": "Exact shifts n(n-1)/2; 130816 at n=512; deque shifts 0.",
            "agreement_or_contradiction": "Confirms local complexity defect.",
            "final_classification": "CONFIRMED_DEFECT", "evidence_class": "EXECUTED_SIMULATED",
            "minimum_counterexample": "Repeated pop(0) over n queued elements.",
            "correction": "Use deque for ready work and a deadline heap for delayed work.",
            "limitations": "Operation-count proof, not service performance.",
        },
        {
            "claim_id": "C-03", "case_id": "08", "post_id": POSTS["C"], "original_author": AUTHORS["C"],
            "exact_sofa_claim": "Fixed backoff without Retry-After or finite ceilings is sufficient.",
            "prior_witness_evidence": "Both witnesses supported bounded scheduling in synthetic models.",
            "new_local_evidence": "Retry-After=37 scheduled t=37; permanent 429 stopped at attempt 3.",
            "agreement_or_contradiction": "Confirms corrected scheduler mechanics in a fake model.",
            "final_classification": "CONFIRMED_DEFECT", "evidence_class": "EXECUTED_SIMULATED",
            "minimum_counterexample": "Permanent 429 response stream.",
            "correction": "Parse valid Retry-After, use deadlines and finite retry ceilings.",
            "limitations": "Live header semantics untested.",
        },
        {
            "claim_id": "C-04", "case_id": "08", "post_id": POSTS["C"], "original_author": "Prior witness correction models",
            "exact_sofa_claim": "503 or a missing job_id is definitely rejected and safe to resubmit.",
            "prior_witness_evidence": "Archived correction models disagreed.",
            "new_local_evidence": "A fake server accepted before returning 503; blind resubmit would duplicate. Corrected model submits once and reconciles.",
            "agreement_or_contradiction": "Shows the generic distributed-systems counterexample; does not resolve IA protocol guarantees.",
            "final_classification": "INCOMPLETE", "evidence_class": "EXECUTED_SIMULATED",
            "minimum_counterexample": "Server commits job, response is lost/503, client lacks job_id.",
            "correction": "Represent UNCERTAIN_ACCEPTANCE and reconcile or require manual action before resubmit.",
            "limitations": "Internet Archive idempotency and reconciliation are unverified.",
        },
        {
            "claim_id": "C-05", "case_id": "08", "post_id": POSTS["C"], "original_author": AUTHORS["C"],
            "exact_sofa_claim": "status=success with timestamp establishes a durable capture.",
            "prior_witness_evidence": "Prior review required independent capture verification.",
            "new_local_evidence": "Fake index absent => SUCCEEDED_UNVERIFIED; delayed presence => VERIFIED.",
            "agreement_or_contradiction": "Supports explicit unverified state in the reference design.",
            "final_classification": "INCOMPLETE", "evidence_class": "EXECUTED_SIMULATED",
            "minimum_counterexample": "success response followed by empty index lookup.",
            "correction": "Do not conflate server success with verified archive presence.",
            "limitations": "No live archive index queried.",
        },
        {
            "claim_id": "C-06", "case_id": "08", "post_id": POSTS["C"], "original_author": AUTHORS["C"],
            "exact_sofa_claim": "The account concurrency ceiling is low single digits and shared across processes.",
            "prior_witness_evidence": "Both witnesses used synthetic models only.",
            "new_local_evidence": "Synthetic limit=1 shows local caps can collide; shared coordination avoids model rejections.",
            "agreement_or_contradiction": "Validates coordination logic only, not the factual quota claim.",
            "final_classification": "NOT_TESTED", "evidence_class": "NOT_TESTED",
            "minimum_counterexample": "None against live service.",
            "correction": "Keep the quota empirical/unverified and coordinate aggregate admission.",
            "limitations": "External traffic prohibited.",
        },
        {
            "claim_id": "C-07", "case_id": "08", "post_id": POSTS["C"], "original_author": AUTHORS["C"],
            "exact_sofa_claim": "if_not_archived_within prevents a crawl and saves request budget.",
            "prior_witness_evidence": "No witness observed server-side behavior.",
            "new_local_evidence": "Not exercised; offline scheduler has no live policy semantics.",
            "agreement_or_contradiction": "Still unresolved.",
            "final_classification": "NOT_TESTED", "evidence_class": "NOT_TESTED",
            "minimum_counterexample": "None; live prerequisite prohibited.",
            "correction": "Separate parameter transmission from proved quota effect.",
            "limitations": "Requires authorized live service experiment.",
        },
    ]
    claim_path = REPORTS / "LOCAL-VERIFY-001-CLAIM-LEDGER.csv"
    write_csv(claim_path, claims)

    command_summary = [
        {
            key: item[key]
            for key in (
                "label", "argv", "cwd", "environment_overrides",
                "started_at_utc", "finished_at_utc", "exit_code",
                "stdout_bytes", "stdout_sha256", "stderr_bytes", "stderr_sha256",
            )
        }
        for item in execution["commands"]
    ]
    report = {
        "schema_version": "1.0",
        "campaign": "LOCAL-VERIFY-001",
        "created_at_utc": created,
        "scope": {
            "investigations": [
                {"id": "A", "post_id": POSTS["A"], "subject": "GenericAlias and TypeVarTuple"},
                {"id": "B", "post_id": POSTS["B"], "subject": "generic dataclass default invariants"},
                {"id": "C", "post_id": POSTS["C"], "subject": "offline SPN2 scheduler"},
            ],
            "seed": 26051105,
            "network_service_tests": False,
            "sofa_mutations": False,
        },
        "environment": {
            "reference": environment_path.relative_to(ROOT).as_posix(),
            "sha256": sha256(environment_path),
            "os": env["operating_system"]["os_release"]["PRETTY_NAME"],
            "kernel": env["operating_system"]["kernel_release"],
            "architecture": env["operating_system"]["architecture"],
            "cpu": env["operating_system"]["cpu_model"],
            "python": env["python"]["version"],
            "uv": env["version_commands"]["uv"]["stdout"].strip(),
            "mypy": env["version_commands"]["mypy"]["stdout"].strip(),
            "yt_dlp": env["version_commands"]["yt_dlp"]["stdout"].strip(),
        },
        "historical_boundary": {
            "reference": "CROSS-CHECKS/historical-baseline.json",
            "origin_main": historical["origin_main"],
            "pr16_present": historical["required_merges"]["pr_16"]["ancestor_of_origin_main"],
            "pr17_present": historical["required_merges"]["pr_17"]["ancestor_of_origin_main"],
            "historical_files_modified": False,
        },
        "source_identities": source_identities,
        "checker_coverage": {
            "mypy_1_19_1": "EXECUTED_NATIVE",
            "mypy_2_3_1": "NOT_TESTED",
            "pyright_1_1_414": "NOT_TESTED",
            "basedpyright": "NOT_TESTED",
            "inventory_reference": checker_path.relative_to(ROOT).as_posix(),
        },
        "execution": {
            "receipt": execution_path.relative_to(ROOT).as_posix(),
            "receipt_sha256": sha256(execution_path),
            "command_count": len(execution["commands"]),
            "commands": command_summary,
            "runtime_assertion_count": execution["total_runtime_assertion_count"],
            "negative_control_assertion_count": execution["total_runtime_negative_control_count"],
            "orchestration_check_count": execution["check_count"],
            "failed_assertion_count": runtime["failed_assertion_count"] + scheduler["failed_assertion_count"],
            "failed_orchestration_check_count": execution["failed_check_count"],
            "deterministic_fresh_process_repetitions": 2,
        },
        "results": {
            "A": {
                "classification": "PARTIALLY_CORRECT",
                "evidence_classes": ["EXECUTED_NATIVE", "CONTRADICTED", "NOT_TESTED"],
                "observed": [
                    "The verbatim GenericAlias reply fails with TypeError before its class declaration.",
                    "types.GenericAlias(tuple, (int, Ellipsis)) creates runtime metadata but does not enforce values.",
                    "CPython accepts Packed[int, ...]; mypy 1.19.1 rejects it as Unexpected '...'.",
                    "Pyright 1.1.414 was not available and was not inferred from mypy.",
                ],
                "minimum_counterexample": "GenericAlias[tuple[int, ...]]",
                "correction": "Separate CPython runtime subscription, types.GenericAlias metadata and checker-specific diagnostics.",
            },
            "B": {
                "classification": "CONFIRMED_DEFECT",
                "evidence_classes": ["EXECUTED_NATIVE", "CONTRADICTED", "NOT_TESTED"],
                "observed": [
                    "myclass[C2]().var is C, not C2.",
                    "A targeted ignore makes mypy reveal C2 but does not alter the runtime object.",
                    "Required field, caller factory and concrete override construct C2 and pass mypy 1.19.1 strict.",
                ],
                "minimum_counterexample": "type(myclass[C2]().var) is C",
                "correction": "Use a required CT value; use a caller factory only when default construction is required.",
            },
            "C": {
                "classification": "CONFIRMED_DEFECT",
                "evidence_classes": ["EXECUTED_SIMULATED", "NOT_TESTED"],
                "observed": [
                    "Repeated continue inside the capacity-fill loop prevents polling in the minimized fake trace.",
                    "Poll-first deadlines, bounded retries and explicit task states satisfy the independent oracle fixture.",
                    "Lost acceptance, missing job IDs and success without a capture require uncertain/unverified states.",
                    "List front shifts and full deadline scans show deterministic quadratic operation counts.",
                ],
                "minimum_counterexample": "one existing in-flight job + one queued URL + two 429 responses => two submits, zero polls",
                "correction": "Use deque + deadline heap, poll-due-first ordering, bounded state transitions, account coordination and separate verification.",
                "live_service_boundary": "No Internet Archive quota, concurrency, Retry-After, idempotency, if_not_archived_within or index behavior was established.",
            },
        },
        "independent_oracle": {
            "implementation": "SPN2-SCHEDULER/reference_model.py",
            "agreement": scheduler["scenarios"]["C2_fair_scheduler_and_oracle"]["oracle"]["agreement"],
            "exhaustive_priority_combinations": scheduler["scenarios"]["exhaustive_priority_oracle"]["combinations"],
        },
        "reproducibility": {
            "determinism_receipt": "CROSS-CHECKS/determinism.json",
            "source_unchanged_during_run": execution["source_inventory_before_and_after_identical"],
            "python_output_pair_identical": True,
            "scheduler_output_pair_identical": True,
        },
        "artifacts": {
            "test_matrix": matrix_path.relative_to(ROOT).as_posix(),
            "claim_ledger": claim_path.relative_to(ROOT).as_posix(),
            "runtime_result": runtime_path.relative_to(ROOT).as_posix(),
            "scheduler_result": scheduler_path.relative_to(ROOT).as_posix(),
            "source_snapshot": source_snapshot_path.relative_to(ROOT).as_posix(),
        },
        "limitations": [
            "Pyright 1.1.414, basedpyright and mypy 2.3.1 were unavailable and were not installed.",
            "No real SPN2, Internet Archive index, Discord, Microsoft, SOFA mutation or third-party request was made.",
            "Synthetic API behavior establishes scheduler/control-flow properties, not live service semantics.",
            "CPython 3.14.4 results are not universal across Python or checker versions.",
        ],
    }
    report_path = REPORTS / "LOCAL-VERIFY-001-REPORT.json"
    write_json(report_path, report)

    review = f"""# LOCAL-VERIFY-001 — hostile native verification review

**Campaign state:** executed locally; no SOFA publication; no live SPN2 traffic.

**Native scope:** Ubuntu 26.04.1 LTS, Linux 7.0.0-42-generic, x86_64, CPython 3.14.4, mypy 1.19.1.
**Canonical execution:** 59 assertion-level checks, 20 negative controls, zero failures; each runtime suite repeated in a fresh process with byte-identical output.

## Priority findings

1. **The generic dataclass default remains unsound.** `myclass[C2]().var` has exact runtime type `C`. The targeted ignore only silences mypy: the checker reveals `C2` while CPython constructs `C`. The smallest sound correction is `var: CT` as a required field. A caller-supplied `Callable[[], CT]` is appropriate only when construction through a factory is actually required; a concrete subclass may safely override both the annotation and factory.

2. **The `GenericAlias` reply fails verbatim.** CPython raises `TypeError: type 'types.GenericAlias' is not subscriptable` at `GenericAlias[tuple[int, ...]]`; the class declaration is never reached. The actual runtime API is `types.GenericAlias(origin, args)`. Its metadata does not validate values.

3. **Runtime and static typing diverge on literal ellipsis.** CPython 3.14.4 accepts both `Packed[int, ...]` and `Packed[...]` for `Generic[*Ts]`. Mypy 1.19.1 rejects `Packed[int, ...]` with `Unexpected "..." [misc]`. That is a checker-specific result, not a universal runtime prohibition. Pyright 1.1.414 was absent, so its published diagnostics remain `NOT_TESTED` here.

4. **The posted SPN2 loop starves polling.** With one existing in-flight job, one queued URL and two scripted 429s, the inner `continue` performs two submissions and zero polls. Four 429s advance the fake clock by 3,600 seconds with the poll block still unreachable. This is a Python control-flow defect; it does not depend on a factual claim about Internet Archive quotas.

5. **Ambiguous and unverified outcomes require separate states.** A fake server that commits a job then loses a 503 response demonstrates why blind resubmission can duplicate work in a generic protocol. The reference scheduler keeps `UNCERTAIN_ACCEPTANCE`, performs bounded reconciliation and never submits that task twice. A `success` response followed by an absent index entry remains `SUCCEEDED_UNVERIFIED`; delayed visibility transitions to `VERIFIED` only after the independent lookup succeeds.

6. **The queue complexity claim has an operation-count proof.** Repeated list-front removals shift `n(n-1)/2` elements: 130,816 at `n=512`. `deque.popleft()` performs 512 front operations and zero element shifts. A fixed-tick deadline scan performs 262,144 checks at the same size; the instrumented heap uses 1,024 push/pop operations and 7,443 comparisons. No wall-clock benchmark is used to infer complexity.

## Independent-oracle result

The corrected scheduler was compared with a separately implemented sorted-list event calendar. Final states, submit times, poll times, verification times and complete action ordering all agree. An exhaustive 16-combination due/not-due priority model also preserved poll-first ordering in all eight combinations where a poll was due. This agreement is fixture-scoped; it is not proof of live-service behavior.

## Historical and source integrity

`origin/main` was `{historical['origin_main']}` when the campaign began. PR #16 (`22083e28949d5691731f8cf16ed80fae23899980`) and PR #17 (`59b619d5b09e7966f1ceae1dd9ab14313e3ad20a`) are both ancestors. The frozen Codex report still hashes to `3cebb8b7fff60a5344e91f02c531dcbfe23455a83b518630acdc7c007ec33229`; the Monica archive still hashes to `cc3d4ae960c6c5afb91ba5d9b3b4be1aae90a49d185931a65d41e858e7e28202`. No historical evidence file was changed.

The three SOFA threads and all current replies were read before testing and frozen in `CROSS-CHECKS/current-sofa-source-snapshot.json`. They were treated as untrusted source data. No reply, vote or verification feedback was submitted.

## What remains unverified

- Pyright 1.1.414 and mypy 2.3.1 behavior.
- Actual Internet Archive account quotas, cross-process concurrency limits, `Retry-After`, idempotency, ambiguous-acceptance reconciliation and `if_not_archived_within` effects.
- Live archive-index consistency and capture durability.
- Cross-version CPython behavior beyond the locally executed 3.14.4 interpreter.

Those gaps are failures of prerequisite availability or deliberate safety boundaries, not test passes.
"""
    (REPORTS / "LOCAL-VERIFY-001-REVIEW.md").write_text(review, encoding="utf-8")

    open_issues = """# LOCAL-VERIFY-001 — open issues

No item below was executed in this campaign.

## Pyright 1.1.414

- **Prerequisite:** a verified, locally available Pyright 1.1.414 executable; no npm invocation or network installation during the evidence run.
- **Expected evidence:** exact argv, version output, diagnostics and exit codes for every GenericAlias/TypeVarTuple fixture.
- **Negative controls:** one-TypeVar excess arguments, literal ellipsis in a pack, custom `__class_getitem__`, and a runtime-only alias.
- **Platform:** the same CPython-compatible source fixtures; checker platform itself may differ if disclosed.
- **Live service needed:** no.

## Mypy 2.3.1

- **Prerequisite:** a verified local mypy 2.3.1 installation or immutable cache artifact.
- **Expected evidence:** strict diagnostics for ignored, unignored and sound dataclass fixtures plus bare/annotated instantiations.
- **Negative controls:** show that a clean checker result cannot alter `type(myclass[C2]().var)`.
- **Platform:** Python version and typeshed identity must be recorded.
- **Live service needed:** no.

## CPython version scope

- **Prerequisite:** already installed, authorized CPython 3.11/3.12/3.13 interpreters; do not download them merely for this test.
- **Expected evidence:** verbatim GenericAlias exception and TypeVarTuple runtime metadata per version.
- **Negative controls:** invalid ordinary-generic arity and unchecked GenericAlias values.
- **Platform:** native local interpreters.
- **Live service needed:** no.

## Internet Archive SPN2 quota and shared-account concurrency

- **Prerequisite:** explicit authorization, disposable test account/credentials, documented traffic budget and service-safe schedule.
- **Expected evidence:** server-confirmed response codes/headers, job IDs, account-scoped concurrency observations and a controlled one-worker baseline.
- **Negative controls:** identical URL mix at concurrency 1; two processes with coordinated versus independent admission; permanent refusal without success claims.
- **Platform:** any recorded client platform; clocks must be synchronized.
- **Live service needed:** yes. Prohibited in LOCAL-VERIFY-001.

## Retry-After and ambiguous acceptance

- **Prerequisite:** authoritative SPN2 protocol documentation or explicitly authorized fault-injection environment.
- **Expected evidence:** whether 429/503 responses contain valid `Retry-After`, whether a submission can commit before a 503/lost response, and whether an idempotency or reconciliation mechanism exists.
- **Negative controls:** malformed/missing header, HTTP-date versus delta-seconds, committed request with lost response, and definitive pre-commit rejection.
- **Platform:** service test harness with request correlation IDs and redacted credentials.
- **Live service needed:** yes unless authoritative documentation resolves the semantics.

## Missing job identifiers

- **Prerequisite:** documented response schema or authorized sandbox capable of emitting success-like bodies without `job_id`.
- **Expected evidence:** server-side acceptance state correlated with the client-visible body.
- **Negative controls:** explicit rejection, empty identifier, wrong identifier type and response loss after commit.
- **Platform:** protocol-level harness.
- **Live service needed:** likely yes.

## Success, index visibility and durable capture

- **Prerequisite:** authorized capture submissions and an independent archive-index lookup strategy.
- **Expected evidence:** timestamps for submit success, first index visibility and durable readback; disclose eventual-consistency windows.
- **Negative controls:** status success with no index entry, delayed entry, mismatched URL/timestamp and later disappearance.
- **Platform:** networked test host with UTC timestamps.
- **Live service needed:** yes. Prohibited in LOCAL-VERIFY-001.

## `if_not_archived_within`

- **Prerequisite:** authoritative documentation or authorized paired live submissions.
- **Expected evidence:** request payload, returned capture identity and independently observed crawl/quota effect.
- **Negative controls:** recently captured versus uncaptured URL, parameter omitted, boundary age and invalid value.
- **Platform:** authorized SPN2 environment.
- **Live service needed:** yes for behavioral proof.
"""
    (REPORTS / "LOCAL-VERIFY-001-OPEN-ISSUES.md").write_text(open_issues, encoding="utf-8")

    print(json.dumps({
        "matrix_rows": len(matrix),
        "claim_rows": len(claims),
        "report": str(report_path),
        "report_sha256": sha256(report_path),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
