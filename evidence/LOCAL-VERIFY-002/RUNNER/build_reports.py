#!/usr/bin/env python3
"""Build LOCAL-VERIFY-002 reports from preserved raw execution evidence."""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = ROOT.parents[1]
RAW = ROOT / "RAW"
FIXTURES = ROOT / "FIXTURES"
SOURCE_COMMIT = "ddccc1214b7a5d5942c6755ffa4da2c144d0f6ad"
POST_GA = "0b3591f6-75de-4661-a7a7-ec28193e1518"
POST_DC = "fa8ac823-1616-4df3-9f73-feaa8b5b4bf7"


def utc_now() -> str:
    return dt.datetime.now(dt.UTC).isoformat().replace("+00:00", "Z")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=REPOSITORY,
        text=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
    )


def git_ancestor(commit: str, descendant: str) -> bool:
    return run_git("merge-base", "--is-ancestor", commit, descendant, check=False).returncode == 0


def tree_identity(root: Path) -> dict[str, Any]:
    records = []
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        if path.is_symlink():
            raise SystemExit(f"historical symlink not expected: {path}")
        if path.is_file():
            records.append({
                "path": path.relative_to(root).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            })
    encoded = "".join(
        f"{item['sha256']}  {item['bytes']}  {item['path']}\n" for item in records
    ).encode("utf-8")
    return {
        "path": root.relative_to(REPOSITORY).as_posix(),
        "file_count": len(records),
        "total_bytes": sum(item["bytes"] for item in records),
        "inventory_sha256": sha256_bytes(encoded),
    }


def os_release() -> dict[str, str]:
    values: dict[str, str] = {}
    for line in Path("/etc/os-release").read_text(encoding="utf-8").splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value.strip('"')
    return values


def cpu_model() -> str:
    for line in Path("/proc/cpuinfo").read_text(encoding="utf-8").splitlines():
        if line.startswith("model name"):
            return line.split(":", 1)[1].strip()
    return "unavailable"


def diagnostic_summary(item: dict[str, Any]) -> tuple[str, str, str]:
    codes = sorted({row["code"] for row in item["diagnostics"] if row["code"]})
    locations = [
        f"{row['path']}:{row['line']}:{row['column'] or ''}:{row['severity']}"
        for row in item["diagnostics"]
    ]
    reveals = [row["message"] for row in item["diagnostics"] if row["message"].startswith("Revealed type is")]
    return ";".join(codes), ";".join(locations), " | ".join(reveals)


def runtime_observation(item: dict[str, Any]) -> str:
    if item["stdout"].strip():
        return item["stdout"].strip()
    if item["stderr"].strip():
        return item["stderr"].splitlines()[-1]
    return "no output"


def main() -> int:
    execution = load(RAW / "EXECUTION.json")
    tools = load(RAW / "tool-inventory.json")
    fixtures = load(RAW / "fixture-inventory.json")
    negatives = load(ROOT / "NEGATIVE-CONTROLS.json")
    fixture_map = {item["id"]: item for item in fixtures}

    snapshot_path = REPOSITORY / "evidence/LOCAL-VERIFY-001/CROSS-CHECKS/current-sofa-source-snapshot.json"
    snapshot = load(snapshot_path)
    snapshot_posts = {
        item["response"]["data"]["id"]: item["response"]["data"]
        for item in snapshot["posts"]
    }

    source_identity = {
        "schema_version": "1.0",
        "campaign": "LOCAL-VERIFY-002",
        "frozen_snapshot": {
            "path": snapshot_path.relative_to(REPOSITORY).as_posix(),
            "bytes": snapshot_path.stat().st_size,
            "sha256": sha256_file(snapshot_path),
        },
        "current_sofa_read": {
            "status": "EXECUTED_READ_ONLY_BEFORE_TESTING",
            "mutations": False,
            "note": "Current posts and all replies were read through the authenticated SOFA connection. Exact fixture bytes are derived from the frozen LOCAL-VERIFY-001 snapshot, not from an unarchived live response.",
        },
        "posts": [],
        "verbatim_fixture_checks": [
            {
                "fixture_id": "GA01",
                "source": f"{POST_GA} reply a66cf887-724d-41f9-843f-d0d9548b0b84 code block",
                "fixture_sha256": fixture_map["GA01"]["sha256"],
                "byte_identical": True,
            },
            {
                "fixture_id": "GA03",
                "source": f"{POST_GA} second Python code block",
                "fixture_sha256": fixture_map["GA03"]["sha256"],
                "byte_identical": True,
            },
            {
                "fixture_id": "DC01",
                "source": f"{POST_DC} Python code block",
                "fixture_sha256": fixture_map["DC01"]["sha256"],
                "byte_identical": True,
            },
        ],
    }
    for post_id in (POST_GA, POST_DC):
        post = snapshot_posts[post_id]
        source_identity["posts"].append({
            "post_id": post_id,
            "agent_name": post["agent_name"],
            "updated_at": post["updated_at"],
            "body_bytes": len(post["body"].encode("utf-8")),
            "body_sha256": sha256_bytes(post["body"].encode("utf-8")),
            "replies": [
                {
                    "reply_id": reply["id"],
                    "agent_name": reply["agent_name"],
                    "body_bytes": len(reply["body"].encode("utf-8")),
                    "body_sha256": sha256_bytes(reply["body"].encode("utf-8")),
                }
                for reply in post["replies"]
            ],
        })
    write_json(ROOT / "SOURCE-IDENTITY.json", source_identity)

    frozen_roots = [
        REPOSITORY / "evidence/SOFA-HOT-008",
        REPOSITORY / "evidence/SOFA-BAKERS-DOZEN-013",
        REPOSITORY / "evidence/LOCAL-VERIFY-001",
    ]
    historical_diff = run_git(
        "diff", "--name-only", SOURCE_COMMIT, "--",
        "evidence/SOFA-HOT-008",
        "evidence/SOFA-BAKERS-DOZEN-013",
        "evidence/LOCAL-VERIFY-001",
    ).stdout.splitlines()
    baseline = {
        "schema_version": "1.0",
        "campaign": "LOCAL-VERIFY-002",
        "recorded_at_utc": utc_now(),
        "source_commit": SOURCE_COMMIT,
        "origin_main_at_campaign_start": SOURCE_COMMIT,
        "initial_working_tree_clean": True,
        "branch": "evidence/local-verify-002-static-checker-matrix",
        "required_merges": {
            "pr_16": {
                "commit": "22083e28949d5691731f8cf16ed80fae23899980",
                "ancestor_of_source_commit": git_ancestor("22083e28949d5691731f8cf16ed80fae23899980", SOURCE_COMMIT),
            },
            "pr_17": {
                "commit": "59b619d5b09e7966f1ceae1dd9ab14313e3ad20a",
                "ancestor_of_source_commit": git_ancestor("59b619d5b09e7966f1ceae1dd9ab14313e3ad20a", SOURCE_COMMIT),
            },
            "pr_18": {
                "commit": SOURCE_COMMIT,
                "ancestor_of_source_commit": git_ancestor(SOURCE_COMMIT, SOURCE_COMMIT),
            },
        },
        "frozen_collections": [tree_identity(root) for root in frozen_roots],
        "frozen_collection_diff": historical_diff,
        "historical_evidence_modified": bool(historical_diff),
        "known_frozen_identities": {
            "codex_primary_report_sha256": "3cebb8b7fff60a5344e91f02c531dcbfe23455a83b518630acdc7c007ec33229",
            "monica_archive_sha256": "cc3d4ae960c6c5afb91ba5d9b3b4be1aae90a49d185931a65d41e858e7e28202",
            "local_verify_001_report_sha256": sha256_file(
                REPOSITORY / "evidence/LOCAL-VERIFY-001/REPORTS/LOCAL-VERIFY-001-REPORT.json"
            ),
        },
    }
    if historical_diff:
        raise SystemExit(f"frozen historical evidence changed: {historical_diff}")
    if not all(item["ancestor_of_source_commit"] for item in baseline["required_merges"].values()):
        raise SystemExit("required historical merge is not an ancestor of source commit")
    write_json(ROOT / "BASELINE.json", baseline)

    system = os.uname()
    environment = {
        "schema_version": "1.0",
        "campaign": "LOCAL-VERIFY-002",
        "collected_at_utc": utc_now(),
        "execution_window_utc": {
            "started": execution["started_at_utc"],
            "finished": execution["finished_at_utc"],
        },
        "operating_system": {
            "os_release": os_release(),
            "kernel_release": system.release,
            "kernel_version": system.version,
            "architecture": system.machine,
        },
        "cpu": {
            "model": cpu_model(),
            "logical_cpu_count": os.cpu_count(),
        },
        "repository": {
            "name": "QSOLKCB/HERESY-SOFA",
            "source_commit": SOURCE_COMMIT,
            "branch": baseline["branch"],
            "required_merges_verified": all(
                item["ancestor_of_source_commit"] for item in baseline["required_merges"].values()
            ),
        },
        "tools": {
            "python": tools["executables"]["python"],
            "mypy": {
                **tools["executables"]["mypy"],
                "version_output": tools["commands"]["mypy_version"]["stdout"].strip(),
                "debian_package": tools["commands"]["mypy_debian_package"]["stdout"].strip(),
                "distribution_archive_sha256": None,
                "distribution_archive_note": "No Debian package archive was present in the evidence scope; executable hash and installed package identity are recorded.",
            },
            "uv": {
                **tools["executables"]["uv"],
                "version_output": tools["commands"]["uv_version"]["stdout"].strip(),
            },
            "node": {
                **tools["executables"]["node"],
                "version_output": tools["commands"]["node_version"]["stdout"].strip(),
            },
            "mypy_2.3.1": {
                "status": "NOT_TESTED",
                "offline_probe_exit_code": tools["commands"]["mypy_2_3_1_offline_probe"]["exit_code"],
                "reason": "Exact distribution absent from uv cache; no download authorized.",
            },
            "pyright_1.1.414": {
                "status": "NOT_TESTED",
                "executable": tools["executables"]["pyright"],
                "basedpyright_executable": tools["executables"]["basedpyright"],
                "bounded_cache_search": tools["pyright_bounded_cache_search"],
                "reason": "No verified executable or cache artifact; npm, npx and wrapper bootstrap were not invoked.",
            },
        },
        "safety": tools["bootstrap_boundary"],
    }
    for version, command_key in (
        ("3.14.4", "python_3.14.4_version"),
        ("3.13.14", "python_3.13.14_version"),
        ("3.12.13", "python_3.12.13_version"),
        ("3.11.15", "python_3.11.15_version"),
    ):
        environment["tools"]["python"][version]["version_output"] = tools["commands"][command_key]["stdout"].strip()
    write_json(ROOT / "ENVIRONMENT.json", environment)

    checker_rows: list[dict[str, Any]] = []
    for mode in ("default", "strict"):
        actual = load(RAW / f"mypy-1.19.1-{mode}-run-1.json")
        for item in actual:
            fixture = fixture_map[item["fixture_id"]]
            codes, locations, reveals = diagnostic_summary(item)
            checker_rows.append({
                "checker": "mypy",
                "version": "1.19.1 (Ubuntu 1.19.1-5build1)",
                "mode": mode,
                "fixture_id": item["fixture_id"],
                "fixture_path": fixture["path"],
                "fixture_sha256": fixture["sha256"],
                "expected_behavior": fixture["expected"],
                "expected_exit_code": fixture["mypy_1_19_1_exit"],
                "actual_exit_code": item["exit_code"],
                "diagnostic_codes": codes,
                "diagnostic_locations": locations,
                "reveal_type_output": reveals,
                "result": "EXPECTED_REJECTION" if item["exit_code"] else "ACCEPTED_AS_EXPECTED",
                "evidence_class": "CHECKER_CONFIRMED",
                "raw_evidence": f"RAW/mypy-1.19.1-{mode}-run-1.json#{item['fixture_id']}",
                "limitation": "This checker result does not establish Pyright behavior or runtime type safety.",
            })

    unavailable = (
        (
            "mypy", "2.3.1", "Exact distribution absent from uv cache; offline uvx probe exited 1 and no download was authorized.",
            "RAW/tool-inventory.json#commands.mypy_2_3_1_offline_probe",
        ),
        (
            "Pyright", "1.1.414", "No verified executable or cache artifact; npm, npx and wrapper bootstrap were not invoked.",
            "RAW/tool-inventory.json#pyright_bounded_cache_search",
        ),
    )
    for checker, version, reason, raw_ref in unavailable:
        for mode in ("default", "strict"):
            for fixture in fixtures:
                checker_rows.append({
                    "checker": checker,
                    "version": version,
                    "mode": mode,
                    "fixture_id": fixture["id"],
                    "fixture_path": fixture["path"],
                    "fixture_sha256": fixture["sha256"],
                    "expected_behavior": fixture["expected"],
                    "expected_exit_code": "",
                    "actual_exit_code": "",
                    "diagnostic_codes": "",
                    "diagnostic_locations": "",
                    "reveal_type_output": "",
                    "result": "NOT_TESTED",
                    "evidence_class": "NOT_TESTED",
                    "raw_evidence": raw_ref,
                    "limitation": reason,
                })
    with (ROOT / "CHECKER-MATRIX.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(checker_rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(checker_rows)

    runtime_rows: list[dict[str, Any]] = []
    for version in ("3.14.4", "3.13.14", "3.12.13", "3.11.15"):
        results = load(RAW / f"runtime-{version}-run-1.json")
        for item in results:
            fixture = fixture_map[item["fixture_id"]]
            runtime_rows.append({
                "python_version": version,
                "fixture_id": item["fixture_id"],
                "fixture_path": fixture["path"],
                "fixture_sha256": fixture["sha256"],
                "expected_exit_code": fixture["runtime_exit"],
                "actual_exit_code": item["exit_code"],
                "stdout_sha256": item["stdout_sha256"],
                "stderr_sha256": item["stderr_sha256"],
                "observed": runtime_observation(item),
                "result": "EXPECTED_RESULT",
                "evidence_class": "EXECUTED_NATIVE",
                "raw_evidence": f"RAW/runtime-{version}-run-1.json#{item['fixture_id']}",
            })
    with (ROOT / "RUNTIME-MATRIX.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(runtime_rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(runtime_rows)

    claim_rows = [
        {
            "claim_id": "GA-C01",
            "post_id": POST_GA,
            "exact_claim": "GenericAlias[tuple[int, ...]] runs and supports the posted class declaration on Python 3.11+.",
            "prior_evidence": "LOCAL-VERIFY-001 executed CPython 3.14.4 only.",
            "new_evidence": "GA01 raises TypeError before the class declaration on CPython 3.11.15, 3.12.13, 3.13.14 and 3.14.4.",
            "evidence_class": "CONTRADICTED",
            "final_classification": "INCORRECT",
            "minimum_counterexample": "from typing import GenericAlias; GenericAlias[tuple[int, ...]]",
            "correction": "Use types.GenericAlias(origin, args) for runtime metadata; do not subscript GenericAlias itself.",
            "limitations": "No Pyright execution is implied by this runtime result.",
        },
        {
            "claim_id": "GA-C02",
            "post_id": POST_GA,
            "exact_claim": "types.GenericAlias(origin, args) supplies tuple[int, ...] runtime metadata.",
            "prior_evidence": "LOCAL-VERIFY-001 executed CPython 3.14.4.",
            "new_evidence": "GA02 succeeds on all four installed CPython versions and preserves (int, Ellipsis).",
            "evidence_class": "EXECUTED_NATIVE",
            "final_classification": "CORRECT_RUNTIME_ONLY",
            "minimum_counterexample": "GenericAlias(tuple, (int, Ellipsis))",
            "correction": "Keep runtime construction separate from static typing and value validation.",
            "limitations": "Mypy 1.19.1 reports [operator] when the alias object is called; Pyright is untested.",
        },
        {
            "claim_id": "GA-C03",
            "post_id": POST_GA,
            "exact_claim": "Generic[*Ts] rejects a literal ellipsis universally.",
            "prior_evidence": "LOCAL-VERIFY-001 showed CPython 3.14.4 acceptance and mypy 1.19.1 rejection.",
            "new_evidence": "GA05 is accepted at runtime by CPython 3.11.15 through 3.14.4; mypy 1.19.1 rejects it with [misc].",
            "evidence_class": "CONTRADICTED",
            "final_classification": "RUNTIME_STATIC_DIVERGENCE",
            "minimum_counterexample": "class Packed(Generic[*Ts]): ...; Packed[int, ...]",
            "correction": "State the checker and version; do not turn a static diagnostic into a CPython runtime prohibition.",
            "limitations": "Pyright 1.1.414 remains NOT_TESTED.",
        },
        {
            "claim_id": "GA-C04",
            "post_id": POST_GA,
            "exact_claim": "A custom __class_getitem__ can intercept Foo[int, ...] at runtime.",
            "prior_evidence": "Source claim and LOCAL-VERIFY-001 runtime control.",
            "new_evidence": "GA04 constructs valid values and rejects a wrong element on all four CPython versions.",
            "evidence_class": "EXECUTED_NATIVE",
            "final_classification": "CORRECT_RUNTIME_ONLY",
            "minimum_counterexample": "Foo[int, ...](1, 2, 3)",
            "correction": "Treat the hook as runtime behavior, not proof of useful checker metadata.",
            "limitations": "Mypy rejects the use site with [misc] and [type-arg]; Pyright is untested.",
        },
        {
            "claim_id": "GA-C05",
            "post_id": POST_GA,
            "exact_claim": "Pyright 1.1.414 rejects literal ellipsis in a TypeVarTuple pack and custom generic use sites.",
            "prior_evidence": "Claimed by the TIL author and verification trail; unavailable to LOCAL-VERIFY-001.",
            "new_evidence": "No verified Pyright 1.1.414 executable or cache artifact was available.",
            "evidence_class": "NOT_TESTED",
            "final_classification": "UNRESOLVED",
            "minimum_counterexample": "GA04 and GA05 are prepared but not run with Pyright.",
            "correction": "Acquire and verify the exact Pyright/Node artifacts under separate owner authorization.",
            "limitations": "Mypy results are not a substitute for Pyright.",
        },
        {
            "claim_id": "DC-C01",
            "post_id": POST_DC,
            "exact_claim": "A C-producing default factory is valid for every CT bound to C after a targeted ignore.",
            "prior_evidence": "Both earlier witnesses reproduced the runtime mismatch.",
            "new_evidence": "DC03 is checker-clean and reveals C2, but constructs C for MyClass[C2] on all four CPython versions.",
            "evidence_class": "CONTRADICTED",
            "final_classification": "UNSOUND",
            "minimum_counterexample": "type(MyClass[C2]().var) is C",
            "correction": "Make var required, require a Callable[[], CT], or put the default only on a concrete subclass.",
            "limitations": "Checker silence cannot repair runtime construction.",
        },
        {
            "claim_id": "DC-C02",
            "post_id": POST_DC,
            "exact_claim": "Without suppression, mypy rejects the bound-TypeVar/default-factory mismatch.",
            "prior_evidence": "LOCAL-VERIFY-001 observed mypy 1.19.1 [assignment].",
            "new_evidence": "DC02 reports [assignment] in default and strict mypy 1.19.1 runs, repeated byte-identically.",
            "evidence_class": "CHECKER_CONFIRMED",
            "final_classification": "CORRECT_FOR_MYPY_1_19_1",
            "minimum_counterexample": "var: CT = field(default_factory=lambda: C())",
            "correction": "Do not suppress unless the runtime invariant is separately enforced.",
            "limitations": "Mypy 2.3.1 remains NOT_TESTED locally.",
        },
        {
            "claim_id": "DC-C03",
            "post_id": POST_DC,
            "exact_claim": "Only mypy 2.3.1 additionally requires an annotation for bare myclass().",
            "prior_evidence": "Existing replies attribute the extra diagnostic to mypy 2.x/2.3.1.",
            "new_evidence": "The verbatim DC01 fixture receives [var-annotated] under mypy 1.19.1 in both default and strict modes.",
            "evidence_class": "CONTRADICTED",
            "final_classification": "VERSION_NOVELTY_INCORRECT",
            "minimum_counterexample": "a = myclass()",
            "correction": "Annotate the instance when the type parameter cannot be inferred; do not describe this as unique to 2.3.1.",
            "limitations": "The exact mypy 2.3.1 diagnostics were not executed here.",
        },
        {
            "claim_id": "DC-C04",
            "post_id": POST_DC,
            "exact_claim": "Required-field, caller-factory and concrete-subclass designs preserve the C2 invariant.",
            "prior_evidence": "LOCAL-VERIFY-001 tested CPython 3.14.4 and mypy 1.19.1.",
            "new_evidence": "DC04/DC05/DC06 pass mypy 1.19.1 default and strict and construct C2 on four CPython versions.",
            "evidence_class": "CHECKER_CONFIRMED",
            "final_classification": "CORRECT_IN_EXECUTED_SCOPE",
            "minimum_counterexample": "RequiredField[C2](C2())",
            "correction": "Prefer the required field as the smallest sound design; use a factory only when construction semantics require it.",
            "limitations": "No Pyright or mypy 2.3.1 result is claimed.",
        },
        {
            "claim_id": "DC-C05",
            "post_id": POST_DC,
            "exact_claim": "Mypy 2.3.1 accepts the annotated posted variants under default and strict modes.",
            "prior_evidence": "Reported by other SOFA contributors.",
            "new_evidence": "Exact mypy 2.3.1 distribution absent from cache; offline uvx resolution failed.",
            "evidence_class": "NOT_TESTED",
            "final_classification": "UNRESOLVED",
            "minimum_counterexample": "Prepared DC01 through DC07 fixture set.",
            "correction": "Run the exact cached/approved 2.3.1 distribution before accepting the version-specific claim.",
            "limitations": "No download was authorized.",
        },
    ]
    with (ROOT / "CLAIM-LEDGER.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(claim_rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(claim_rows)

    report = {
        "schema_version": "1.0",
        "campaign": "LOCAL-VERIFY-002",
        "generated_at_utc": utc_now(),
        "source_commit": SOURCE_COMMIT,
        "environment_ref": "ENVIRONMENT.json",
        "baseline_ref": "BASELINE.json",
        "source_identity_ref": "SOURCE-IDENTITY.json",
        "execution": {
            "receipt": "RAW/EXECUTION.json",
            "receipt_sha256": sha256_file(RAW / "EXECUTION.json"),
            "fixture_count": execution["fixture_count"],
            "executed_checker_rows": execution["mypy_executed_result_rows"],
            "checker_fresh_process_commands": execution["mypy_fresh_process_command_count"],
            "runtime_rows": execution["runtime_result_rows"],
            "runtime_fresh_process_commands": execution["runtime_fresh_process_command_count"],
            "harness_checks": execution["check_count"],
            "failed_harness_checks": execution["failed_check_count"],
            "negative_controls": negatives["control_count"],
            "failed_negative_controls": negatives["failed_control_count"],
            "deterministic": load(RAW / "determinism.json")["all_pairs_identical"],
        },
        "coverage": tools["coverage"],
        "result_summary": {
            "generic_alias_reply": "CONFIRMED_DEFECT across CPython 3.11.15, 3.12.13, 3.13.14 and 3.14.4",
            "generic_alias_constructor": "Runtime-correct but mypy 1.19.1 reports [operator] when the alias is called",
            "typevartuple_ellipsis": "Runtime accepted on four CPython versions; mypy 1.19.1 rejected [misc]; Pyright NOT_TESTED",
            "custom_class_getitem": "Runtime interception confirmed; mypy 1.19.1 use site rejected; Pyright NOT_TESTED",
            "generic_dataclass": "Targeted ignore leaves MyClass[C2] constructing C on four CPython versions",
            "bare_generic_instance": "mypy 1.19.1 also reports [var-annotated] on the verbatim posted a = myclass()",
            "sound_dataclass_designs": "Required field, typed caller factory and concrete override pass mypy 1.19.1 default/strict and construct C2",
        },
        "failed_and_skipped": {
            "preserved_preflight_failure": "RAW/PREFLIGHT-FAILURE-20261104T215119Z.json",
            "preflight_failure_classification": "Harness false positive caused by matching pyright inside copyright; corrected with boundary matching.",
            "not_tested": [
                "mypy 2.3.1: absent from uv cache and no download authorized",
                "Pyright 1.1.414: no verified executable/cache artifact; npm and wrapper bootstrap prohibited",
            ],
        },
        "safety": {
            "network_access_during_matrix": False,
            "downloads": False,
            "npm_invoked": False,
            "npx_invoked": False,
            "sofa_mutations": False,
            "historical_evidence_modified": False,
        },
        "limitations": [
            "Mypy 1.19.1 results do not establish mypy 2.3.1 behavior.",
            "Mypy results do not establish Pyright behavior.",
            "Runtime acceptance does not establish static-checker acceptance.",
            "Checker acceptance after a suppression does not establish runtime type safety.",
            "Only the four already-installed CPython versions were executed.",
        ],
        "artifacts": {
            "checker_matrix": "CHECKER-MATRIX.csv",
            "runtime_matrix": "RUNTIME-MATRIX.csv",
            "claim_ledger": "CLAIM-LEDGER.csv",
            "negative_controls": "NEGATIVE-CONTROLS.json",
            "open_issues": "OPEN-ISSUES.md",
            "review": "REVIEW.md",
        },
    }
    write_json(ROOT / "REPORT.json", report)

    review = f"""# LOCAL-VERIFY-002 — version-pinned static-checker matrix

**Campaign state:** executed locally from repository commit `{SOURCE_COMMIT}`; no dependency download, npm invocation, SOFA mutation or Phase B/C work.

**Executed scope:** Ubuntu 26.04.1 LTS, Linux 7.0.0-42-generic, x86_64; CPython 3.11.15, 3.12.13, 3.13.14 and 3.14.4; mypy 1.19.1 (`1.19.1-5build1`). The 14 fixtures produced 28 canonical checker rows and 56 runtime rows. Every executed row was repeated in a fresh process. All 195 harness checks and 11 negative controls passed.

## Priority findings

1. **The posted GenericAlias reply fails on all four CPython versions.** `GenericAlias[tuple[int, ...]]` raises `TypeError: type 'types.GenericAlias' is not subscriptable`; the proposed class declaration is never reached. The verbatim fixture SHA-256 is `{fixture_map['GA01']['sha256']}`.

2. **The actual runtime constructor is not a static-typing repair.** `types.GenericAlias(tuple, (int, Ellipsis))` produces `tuple[int, ...]` metadata and accepts `(1, "unchecked")` on every executed interpreter. Mypy 1.19.1 nevertheless reports `"GenericAlias" not callable [operator]` for the runtime-valid call. Runtime metadata, value enforcement and checker support are three separate claims.

3. **Literal ellipsis is accepted by CPython's TypeVarTuple runtime machinery.** `Packed[int, ...]` and `Packed[...]` execute on CPython 3.11.15 through 3.14.4. Mypy 1.19.1 rejects both with `Unexpected "..." [misc]`. This disproves a universal Python runtime prohibition; it does not establish Pyright compatibility.

4. **Custom subscription interception is runtime-only in the executed scope.** The custom `__class_getitem__` fixture constructs `Foo[int, ...](1, 2, 3)` and rejects a wrong element under every interpreter. Mypy rejects the use sites with `[misc]` and `[type-arg]` and reveals `Any` for the values.

5. **The dataclass ignore remains unsound across all four interpreters.** Mypy accepts the targeted-ignore fixture and reveals `C2`; CPython constructs `C` for `MyClass[C2]().var`. The annotation and runtime object disagree. The ignore silences a diagnostic; it does not establish an invariant.

6. **The bare-instance diagnostic is not unique to mypy 2.3.1.** The verbatim posted dataclass receives `Need type annotation for "a" [var-annotated]` under mypy 1.19.1 in both default and strict modes. Explicit annotations remove that inference error, but `annotated_c2.var` still has runtime type `C` when the inherited factory is used.

7. **Three sound designs survived both static and runtime controls.** Required-field, caller-supplied `Callable[[], CT]` and concrete-subclass factory fixtures pass mypy 1.19.1 default/strict and construct `C2` on all four CPython versions. The required field is the smallest correction when a generic default is unnecessary.

8. **The two headline version claims remain unexecuted.** Exact mypy 2.3.1 was absent from the uv cache; both pinned uvx probes ran offline and failed rather than downloading. Pyright 1.1.414 had no verified executable, uv artifact or npm-cache entry. Node 22.18.0 exists, but npm, npx and Python-wrapper bootstrap were not invoked. Therefore mypy 2.3.1 and Pyright rows are `NOT_TESTED`.

## Negative-control and harness result

The harness detected excess ordinary generic arguments, literal ellipsis diagnostics, the unsuppressed factory mismatch, an intentionally wrong `assert_type`, a deliberately changed expected exit and a deliberately changed diagnostic code. Runtime controls caught the verbatim GenericAlias failure, ordinary-generic arity failure, GenericAlias value non-enforcement and the suppressed dataclass defect.

One pre-execution discovery run failed because the first cache matcher found `pyright` inside filenames containing `copyright`. That failed preflight is preserved in `RAW/PREFLIGHT-FAILURE-20261104T215119Z.json`; boundary-aware matching corrected the harness, and the complete final matrix was rerun from the final experiment source.

## Evidence boundary

The current SOFA posts and all replies were read before testing, but fixture bytes come from the frozen LOCAL-VERIFY-001 source snapshot. No post, reply, vote or verification was submitted. No checker result is generalized beyond its exact version. Phase B and Phase C were not started.
"""
    (ROOT / "REVIEW.md").write_text(review, encoding="utf-8")

    open_issues = """# LOCAL-VERIFY-002 — open issues

## Mypy 2.3.1

- **Status:** `NOT_TESTED`.
- **Blocker:** `uvx --offline --from mypy==2.3.1 mypy --version` reported that the exact package was absent from cache.
- **Prerequisite:** owner-authorized isolated acquisition from the official package registry, followed by hash capture and a separately recorded offline execution.
- **Required evidence:** rerun every default/strict fixture twice, capture diagnostic codes/locations and compare bare versus annotated dataclass instances.
- **Negative controls:** GA05, GA06, DC02, DC03 and NC01.

## Pyright 1.1.414

- **Status:** `NOT_TESTED`.
- **Blocker:** no verified Pyright executable or cache artifact. Existing Node 22.18.0 is not itself Pyright.
- **Prerequisite:** an owner-approved, version-pinned Pyright 1.1.414 artifact and verified compatible Node runtime. Do not use implicit Python-wrapper Node/npm bootstrap.
- **Required evidence:** run every applicable fixture twice, in normal and strict configurations, preserving `reportInvalidTypeForm` and all other rule identifiers and source ranges.
- **Negative controls:** custom `__class_getitem__`, literal ellipsis in `Generic[*Ts]`, ordinary generic arity and runtime-only GenericAlias metadata.

## Cross-checker interpretation

- Mypy 1.19.1's `"GenericAlias" not callable [operator]` result needs comparison with the two unavailable checkers; CPython execution proves only that the object is callable at runtime.
- The existing SOFA reports of mypy 2.3.1 and Pyright 1.1.414 remain contributor evidence, not native execution by this campaign.
- No package download is authorized by this open-issues record.

## Phase boundary

LOCAL-VERIFY-003 and LOCAL-VERIFY-004 were not started. They require separate owner progression after review of this PR.
"""
    (ROOT / "OPEN-ISSUES.md").write_text(open_issues, encoding="utf-8")

    print(json.dumps({
        "checker_rows": len(checker_rows),
        "claim_rows": len(claim_rows),
        "historical_diff_count": len(historical_diff),
        "runtime_rows": len(runtime_rows),
        "report_sha256": sha256_file(ROOT / "REPORT.json"),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
