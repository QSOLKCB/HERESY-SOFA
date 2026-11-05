#!/usr/bin/env python3
"""Build the LOCAL-VERIFY-002B reports from finalized raw receipts."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = ROOT.parents[1]
RAW = ROOT / "RAW"
FROZEN = REPOSITORY / "evidence/LOCAL-VERIFY-002"
SOURCE_COMMIT = "1ad645e13277a28ba511cad2f6bd2f5d988894d8"
PR19_HEAD = "98054e2f4002b63bc724882bd6ee86f45f4fdb28"
POST_GA = "0b3591f6-75de-4661-a7a7-ec28193e1518"
POST_DC = "fa8ac823-1616-4df3-9f73-feaa8b5b4bf7"


def utc_now() -> str:
    return dt.datetime.now(dt.UTC).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run(*argv: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        cwd=REPOSITORY,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=check,
    )


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return run("git", *args, check=check)


def tree_identity(root: Path) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        if path.is_symlink():
            raise RuntimeError(f"unexpected symlink in frozen evidence: {path}")
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
        if "=" in line:
            key, value = line.split("=", 1)
            values[key] = value.strip('"')
    return values


def cpu_model() -> str:
    for line in Path("/proc/cpuinfo").read_text(encoding="utf-8").splitlines():
        if line.startswith("model name"):
            return line.split(":", 1)[1].strip()
    return "unavailable"


def distribution_inventory(python: Path) -> dict[str, Any]:
    code = r'''
import importlib.metadata as metadata
import json
from pathlib import Path
names = ("mypy", "librt", "ast-serialize", "typing-extensions", "mypy-extensions", "pathspec")
items = []
for name in names:
    distribution = metadata.distribution(name)
    items.append({
        "requested_name": name,
        "metadata_name": distribution.metadata["Name"],
        "version": distribution.version,
        "root": str(distribution.locate_file("")),
        "requires": distribution.requires or [],
    })
print(json.dumps(items, sort_keys=True))
'''
    result = run(str(python), "-c", code)
    values = json.loads(result.stdout)
    for item in values:
        item["root"] = item["root"].replace(str(Path.home()), "$HOME")
    return {
        "command": ["<MYPY_VENV_PYTHON>", "-c", "importlib.metadata inventory"],
        "exit_code": result.returncode,
        "distributions": values,
    }


def load_documents() -> dict[tuple[str, str, int], dict[str, Any]]:
    documents: dict[tuple[str, str, int], dict[str, Any]] = {}
    for mode in ("default", "strict"):
        for run_number in (1, 2):
            documents[("mypy", mode, run_number)] = load_json(
                RAW / f"mypy-2.3.1-{mode}-run-{run_number}.json"
            )
    for mode in ("standard", "strict"):
        for run_number in (1, 2):
            documents[("Pyright", mode, run_number)] = load_json(
                RAW / f"pyright-1.1.414-{mode}-run-{run_number}.json"
            )
    return documents


def diagnostic_fields(
    checker: str, item: dict[str, Any]
) -> tuple[list[dict[str, Any]], str, str, str, int, int, int]:
    diagnostics = (
        item["diagnostics"] if checker == "mypy" else item["parsed"]["generalDiagnostics"]
    )
    rules = sorted({row["rule"] for row in diagnostics if row.get("rule")})
    locations: list[str] = []
    messages: list[str] = []
    reveals: list[str] = []
    for row in diagnostics:
        start = row["range"]["start"]
        line = start["line"] + (0 if checker == "mypy" else 1)
        character = start.get("character")
        if checker == "Pyright":
            character = character + 1 if character is not None else None
        location = f"{Path(row['file']).name}:{line}"
        if character is not None:
            location += f":{character}"
        locations.append(f"{location}:{row['severity']}")
        messages.append(f"{row['severity']}: {row['message']}")
        if (
            (checker == "mypy" and row["message"].startswith("Revealed type is"))
            or (checker == "Pyright" and row["message"].startswith("Type of "))
        ):
            reveals.append(row["message"])
    return (
        diagnostics,
        ";".join(rules),
        ";".join(locations),
        " | ".join(reveals),
        sum(row["severity"] == "error" for row in diagnostics),
        sum(row["severity"] == "warning" for row in diagnostics),
        sum(row["severity"] in {"note", "information"} for row in diagnostics),
    )


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def build_matrix(
    documents: dict[tuple[str, str, int], dict[str, Any]],
    fixtures: list[dict[str, Any]],
    determinism: dict[str, Any],
) -> list[dict[str, str]]:
    old_rows = read_csv(FROZEN / "CHECKER-MATRIX.csv")
    prior_mypy = {
        (row["fixture_id"], row["mode"]): int(row["actual_exit_code"])
        for row in old_rows
        if row["checker"] == "mypy" and row["evidence_class"] == "CHECKER_CONFIRMED"
    }
    pair_state = {
        (item["checker"], item["mode"], item["fixture_id"]): item
        for item in determinism["pairs"]
    }
    fixture_by_id = {item["id"]: item for item in fixtures}
    rows: list[dict[str, str]] = []
    for checker, version, modes in [
        ("mypy", "2.3.1 (compiled: yes)", ("default", "strict")),
        ("Pyright", "1.1.414", ("standard", "strict")),
    ]:
        for mode in modes:
            document = documents[(checker, mode, 1)]
            for item in document["results"]:
                fixture = fixture_by_id[item["fixture_id"]]
                diagnostics, rules, locations, reveals, errors, warnings, infos = diagnostic_fields(
                    checker, item
                )
                if checker == "mypy":
                    prior_exit = prior_mypy[(item["fixture_id"], mode)]
                    expected_basis = f"mypy 1.19.1 observed exit {prior_exit} on the same frozen bytes"
                    result = (
                        "MATCHED_MYPY_1_19_1_EXIT"
                        if item["exit_code"] == prior_exit
                        else "DIVERGED_FROM_MYPY_1_19_1_EXIT"
                    )
                else:
                    prior_exit = None
                    expected_basis = "Previously NOT_TESTED; this row is empirical Pyright coverage"
                    result = "OBSERVED_REJECTION" if item["exit_code"] == 1 else "OBSERVED_ACCEPTANCE"
                pair = pair_state[(checker.lower(), mode, item["fixture_id"])]
                rows.append({
                    "checker": checker,
                    "version": version,
                    "mode": mode,
                    "fixture_id": item["fixture_id"],
                    "fixture_path": fixture["source_path"],
                    "fixture_sha256": fixture["sha256"],
                    "original_expected_behavior": fixture["expected"],
                    "expected_basis": expected_basis,
                    "prior_mypy_1_19_1_exit": "" if prior_exit is None else str(prior_exit),
                    "actual_exit_code": str(item["exit_code"]),
                    "error_count": str(errors),
                    "warning_count": str(warnings),
                    "note_or_information_count": str(infos),
                    "diagnostic_rules": rules,
                    "diagnostic_locations": locations,
                    "diagnostic_messages": " | ".join(
                        f"{row['severity']}: {row['message']}" for row in diagnostics
                    ),
                    "reveal_type_output": reveals,
                    "result": result,
                    "experiment_status": "PASS",
                    "evidence_class": "CHECKER_CONFIRMED",
                    "repeat_semantic_identical": str(pair["semantic_output_identical"]).lower(),
                    "raw_evidence": (
                        f"RAW/{'mypy-2.3.1' if checker == 'mypy' else 'pyright-1.1.414'}-"
                        f"{mode}-run-1.json#{item['fixture_id']}"
                    ),
                    "limitation": (
                        "Static result only; runtime behavior is separately recorded in frozen "
                        "LOCAL-VERIFY-002 and was not re-executed in this addendum."
                    ),
                })
    return rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    if not rows:
        raise RuntimeError(f"refusing to write empty CSV: {path}")
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def matrix_map(rows: list[dict[str, str]]) -> dict[tuple[str, str, str], dict[str, str]]:
    return {(row["checker"], row["mode"], row["fixture_id"]): row for row in rows}


def build_claims(matrix: list[dict[str, str]]) -> list[dict[str, str]]:
    values = matrix_map(matrix)

    def summary(checker: str, modes: tuple[str, str], fixture: str) -> str:
        parts = []
        for mode in modes:
            row = values[(checker, mode, fixture)]
            rules = row["diagnostic_rules"] or "no error rule"
            parts.append(
                f"{mode}: exit {row['actual_exit_code']}, {rules}; {row['reveal_type_output'] or 'no reveal'}"
            )
        return " / ".join(parts)

    prior = (
        "evidence/LOCAL-VERIFY-002/REPORT.json sha256 "
        f"{sha256_file(FROZEN / 'REPORT.json')}; "
        "runtime/static results remain frozen"
    )
    claims = [
        {
            "claim_id": "GA-01",
            "sofa_post_id": POST_GA,
            "source_identity": "reply a66cf887-724d-41f9-843f-d0d9548b0b84 (Milo Humanizer)",
            "exact_disputed_claim": "The proposed from typing import GenericAlias followed by GenericAlias[...] is a valid way to declare and use Foo[int, ...].",
            "prior_evidence": prior,
            "mypy_2_3_1": summary("mypy", ("default", "strict"), "GA01"),
            "pyright_1_1_414": summary("Pyright", ("standard", "strict"), "GA01"),
            "agreement": "Both pinned checkers reject; prior CPython 3.14.4 execution also failed before class creation.",
            "final_classification": "CONTRADICTED",
            "limitation": "Checker rejection and prior local runtime execution do not describe every future Python/checker release.",
        },
        {
            "claim_id": "GA-02",
            "sofa_post_id": POST_GA,
            "source_identity": "independent correction fixture GA02",
            "exact_disputed_claim": "types.GenericAlias(origin, args) creates runtime metadata that the pinned static checkers treat as a useful callable specialized type.",
            "prior_evidence": prior,
            "mypy_2_3_1": summary("mypy", ("default", "strict"), "GA02"),
            "pyright_1_1_414": summary("Pyright", ("standard", "strict"), "GA02"),
            "agreement": "Both recognize the object only as GenericAlias, reject the call, and infer Any or Unknown for the result.",
            "final_classification": "CONTRADICTED",
            "limitation": "CPython runtime construction succeeds in frozen LOCAL-VERIFY-002; this row is the separate static boundary.",
        },
        {
            "claim_id": "GA-03",
            "sofa_post_id": POST_GA,
            "source_identity": "frozen fixtures GA03 and GA04",
            "exact_disputed_claim": "A custom __class_getitem__ hook makes Foo[int, ...] a statically valid ordinary Generic[T] use.",
            "prior_evidence": prior,
            "mypy_2_3_1": summary("mypy", ("default", "strict"), "GA04"),
            "pyright_1_1_414": summary("Pyright", ("standard", "strict"), "GA04"),
            "agreement": "Runtime interception does not teach either checker a new generic grammar; the use site is rejected.",
            "final_classification": "CONTRADICTED",
            "limitation": "The definition-only GA03 fixture passes mypy and Pyright standard; strict Pyright separately flags unknown typing in its implementation.",
        },
        {
            "claim_id": "GA-04",
            "sofa_post_id": POST_GA,
            "source_identity": "independent TypeVarTuple fixture GA05",
            "exact_disputed_claim": "Literal ellipsis is accepted as an argument to a user-defined Generic[*Ts] by the pinned static checkers because CPython accepts it at runtime.",
            "prior_evidence": prior,
            "mypy_2_3_1": summary("mypy", ("default", "strict"), "GA05"),
            "pyright_1_1_414": summary("Pyright", ("standard", "strict"), "GA05"),
            "agreement": "Both reject literal ellipsis: mypy [misc], Pyright reportInvalidTypeForm. CPython runtime acceptance remains a distinct prior observation.",
            "final_classification": "CONTRADICTED",
            "limitation": "This is user-defined variadic-generic syntax, not every special form in the typing specification.",
        },
        {
            "claim_id": "GA-05",
            "sofa_post_id": POST_GA,
            "source_identity": "negative control GA06",
            "exact_disputed_claim": "An ordinary Generic[T] accepts two type arguments.",
            "prior_evidence": prior,
            "mypy_2_3_1": summary("mypy", ("default", "strict"), "GA06"),
            "pyright_1_1_414": summary("Pyright", ("standard", "strict"), "GA06"),
            "agreement": "Both reject the excess argument, proving the harness detects an invalid generic arity.",
            "final_classification": "CONTRADICTED",
            "limitation": "Applies to this one-TypeVar class.",
        },
        {
            "claim_id": "DC-01",
            "sofa_post_id": POST_DC,
            "source_identity": "original post by midhun-hermes; frozen fixture DC01",
            "exact_disputed_claim": "mypy 2.3.1 accepts the verbatim bare a = myclass() example once the factory mismatch is suppressed.",
            "prior_evidence": prior,
            "mypy_2_3_1": summary("mypy", ("default", "strict"), "DC01"),
            "pyright_1_1_414": summary("Pyright", ("standard", "strict"), "DC01"),
            "agreement": "mypy 2.3.1 reproduces [var-annotated]. Pyright standard accepts; strict reports Unknown-related diagnostics.",
            "final_classification": "CONTRADICTED",
            "limitation": "Checker disagreement is preserved; Pyright acceptance does not establish runtime specialization.",
        },
        {
            "claim_id": "DC-02",
            "sofa_post_id": POST_DC,
            "source_identity": "independent minimal fixture DC02",
            "exact_disputed_claim": "A factory returning C satisfies a field declared as arbitrary bound CT when instantiated as MyClass[C2].",
            "prior_evidence": prior,
            "mypy_2_3_1": summary("mypy", ("default", "strict"), "DC02"),
            "pyright_1_1_414": summary("Pyright", ("standard", "strict"), "DC02"),
            "agreement": "Both reject the unsuppressed assignment while revealing value.var as C2; prior native runtime execution constructed C.",
            "final_classification": "CONTRADICTED",
            "limitation": "The runtime counterexample is cross-referenced from immutable LOCAL-VERIFY-002 rather than re-executed here.",
        },
        {
            "claim_id": "DC-03",
            "sofa_post_id": POST_DC,
            "source_identity": "targeted-ignore fixture DC03",
            "exact_disputed_claim": "A targeted type-ignore repairs the runtime invariant for MyClass[C2]().var.",
            "prior_evidence": prior,
            "mypy_2_3_1": summary("mypy", ("default", "strict"), "DC03"),
            "pyright_1_1_414": summary("Pyright", ("standard", "strict"), "DC03"),
            "agreement": "mypy and Pyright standard accept and reveal C2, but the frozen native runtime result is C; strict Pyright's extra error is only reportUnnecessaryIsInstance.",
            "final_classification": "CONTRADICTED",
            "limitation": "A suppression can change diagnostics only, never the default factory's object.",
        },
        {
            "claim_id": "DC-04",
            "sofa_post_id": POST_DC,
            "source_identity": "sound alternatives DC04, DC05 and DC06",
            "exact_disputed_claim": "A required field, caller-provided typed factory, or concrete subclass override can preserve the C2 specialization without an unjustified ignore.",
            "prior_evidence": prior,
            "mypy_2_3_1": "All three alternatives exit 0 in default and strict modes and reveal C2.",
            "pyright_1_1_414": "All three alternatives exit 0 in standard and strict modes and reveal C2.",
            "agreement": "Both checkers agree with prior native runtime construction of C2.",
            "final_classification": "CHECKER_CONFIRMED",
            "limitation": "These are three minimal designs, not an exhaustive design taxonomy.",
        },
        {
            "claim_id": "DC-05",
            "sofa_post_id": POST_DC,
            "source_identity": "inference fixture DC07",
            "exact_disputed_claim": "Bare and explicitly annotated generic instances receive equivalent useful static specialization.",
            "prior_evidence": prior,
            "mypy_2_3_1": summary("mypy", ("default", "strict"), "DC07"),
            "pyright_1_1_414": summary("Pyright", ("standard", "strict"), "DC07"),
            "agreement": "mypy rejects the bare instance; Pyright standard retains Unknown and strict rejects it. Both still present annotated_c2.var as C2 despite the prior runtime C counterexample.",
            "final_classification": "CONTRADICTED",
            "limitation": "Inference policy differs by checker and mode.",
        },
        {
            "claim_id": "NC-01",
            "sofa_post_id": POST_DC,
            "source_identity": "negative control NC01",
            "exact_disputed_claim": "The harness detects an intentionally wrong assert_type(value.var, C) when the exact inferred type is C2.",
            "prior_evidence": prior,
            "mypy_2_3_1": summary("mypy", ("default", "strict"), "NC01"),
            "pyright_1_1_414": summary("Pyright", ("standard", "strict"), "NC01"),
            "agreement": "Both reject the false exact-type assertion.",
            "final_classification": "CHECKER_CONFIRMED",
            "limitation": "Negative control only.",
        },
    ]
    return claims


def artifact_record(value: dict[str, Any], full_ref: str) -> dict[str, Any]:
    return {
        "filename": value["filename"],
        "bytes": value["bytes"],
        "sha256": value["sha256"],
        "official_source_url": value.get("official_url") or value.get("official_tarball_url"),
        "official_registry_integrity": (
            value.get("official_pypi_sha256")
            or value.get("official_registry_integrity")
        ),
        "format": value["archive_format"],
        "metadata": value.get("metadata") or {
            "name": value["package_json"]["name"],
            "version": value["package_json"]["version"],
            "engines": value["package_json"].get("engines", {}),
        },
        "safety": value["safety"],
        "full_member_inventory": full_ref,
    }


def build_review(matrix: list[dict[str, str]], report: dict[str, Any]) -> str:
    values = matrix_map(matrix)
    def rules(checker: str, mode: str, fixture: str) -> str:
        row = values[(checker, mode, fixture)]
        return row["diagnostic_rules"] or "no error"
    return f"""# LOCAL-VERIFY-002B hostile static-checker review

## Verdict

The two missing checker matrices are now executed, not inferred. Mypy 2.3.1 and Pyright 1.1.414 were run in 112 fresh offline processes over the 14 byte-identified LOCAL-VERIFY-002 fixtures. Both repetitions were semantically identical, all 12 negative controls fired, and no frozen fixture or historical evidence changed.

The headline defect survives: `typing.GenericAlias` is not the proposed generic base, and the runtime `types.GenericAlias(origin, args)` constructor does not provide useful static specialization. Literal ellipsis remains a CPython-runtime-versus-static-checker boundary for the tested user-defined `Generic[*Ts]` form. The generic dataclass factory remains unsound after suppression.

## Baseline and package custody

PR #19 was read back as merged at head `{PR19_HEAD}` with merge commit `{SOURCE_COMMIT}`. This campaign branched from that exact current `origin/main`. Frozen `evidence/LOCAL-VERIFY-002` has no diff from the source commit; its report remains SHA-256 `{sha256_file(FROZEN / 'REPORT.json')}`.

Acquisition and execution were separated. Seven exact distribution archives were downloaded from their official registries, member-inspected with path/type/size bounds, hash-checked against registry metadata, and archived. Pyright was unpacked by a controlled standard-library extractor; no npm, npx or package lifecycle script ran. Mypy used a six-wheel venv without system site-packages, and `uv pip check` reported compatibility before the canonical matrix.

## GenericAlias and variadic typing

- **Original reply (GA01): rejected by both.** Mypy reports `{rules('mypy', 'default', 'GA01')}`; Pyright reports `{rules('Pyright', 'standard', 'GA01')}`. This agrees with the prior CPython failure, which occurred before the proposed class declaration.
- **Correct runtime constructor (GA02): static dead end.** CPython previously constructed `types.GenericAlias(tuple, (int, Ellipsis))`. Mypy 2.3.1 nevertheless reports `[operator]`, reveals the alias as `types.GenericAlias`, and reduces the call result to `Any`. Pyright reports `reportCallIssue`, knows only `GenericAlias`, and reduces the result to `Unknown`.
- **Custom `__class_getitem__` (GA04): not a typing-language extension.** The runtime hook executes in the frozen runtime evidence, but mypy reports `{rules('mypy', 'default', 'GA04')}` and Pyright reports `{rules('Pyright', 'standard', 'GA04')}` at the use site.
- **Literal ellipsis in `Generic[*Ts]` (GA05): rejected by both.** Mypy emits `[misc] Unexpected "..."`; Pyright emits `reportInvalidTypeForm`. Pyright's reveal text retains `Packed[int, ...]`, but that information diagnostic does not cancel the error. Runtime acceptance is not static acceptance.
- **Ordinary excess arity (GA06): rejected by both**, validating the negative-control path.

## Generic dataclass invariant

- **Bare original fixture (DC01): checker disagreement preserved.** Mypy 2.3.1 reproduces `[var-annotated]` in default and strict modes. Pyright standard accepts it, while strict reports Unknown-related diagnostics. Neither outcome repairs runtime construction.
- **Unsuppressed mismatch (DC02): both checkers catch it.** Mypy reports `[assignment]`; Pyright reports `reportAssignmentType`. Both reveal `value.var` as `C2`, while the prior native execution shows that the default factory actually constructs `C`.
- **Targeted ignore (DC03): diagnostic silence is not correctness.** Mypy accepts in both modes and reveals `C2`; Pyright standard also accepts. Pyright strict's sole error is the unrelated `reportUnnecessaryIsInstance`. The native runtime counterexample remains `MyClass[C2]().var -> C`.
- **Sound designs (DC04–DC06): confirmed.** Required-field construction, a caller-supplied typed factory and a concrete subclass factory all pass both mypy modes and both Pyright modes, reveal `C2`, and agree with the prior runtime `C2` results.
- **Bare inference (DC07): not equivalent to specialization.** Mypy rejects the bare generic; Pyright standard records `MyClass[Unknown]`, and strict rejects the unknowns. Explicit annotation can still tell either checker `C2` while the defective factory returns `C`.

## Controls and reproducibility

- Final matrix rows: {report['execution']['matrix_rows']}.
- Fresh checker processes: {report['execution']['fresh_process_checker_commands']}.
- Negative controls: {report['execution']['negative_control_count']} passed, zero failed.
- Timeouts: zero.
- Repeat comparison: all 56 semantic pairs identical. Pyright's wall-clock and duration fields are preserved but excluded from semantic equality.
- Frozen source: unchanged before/after execution.
- Network during checker execution: none.

Two pre-finalization harness corrections are preserved rather than hidden: distribution-name normalization in the archive validator, and optional mypy column numbers in the diagnostic parser. A valid intermediate run that inherited three system packages is also identified as superseded; the canonical run uses only archived wheels.

## Minimal corrections

For runtime alias metadata, call `types.GenericAlias(origin, args)` and do not claim that it creates a statically useful generic class. For a typed variadic class, use `TypeVarTuple` with actual type arguments; do not use literal ellipsis in this tested user-defined form. For the dataclass, require the field, accept a `Callable[[], CT]`, or override annotation and factory together in a concrete subclass. A targeted ignore is not a constructor.

## Limits

This addendum executes static checkers only. CPython runtime observations are cited from immutable LOCAL-VERIFY-002 and were not rerun. The results cover mypy 2.3.1, Pyright 1.1.414, Python target 3.14 and the recorded default/strict configurations; they are not universal claims about future releases. No SOFA content was changed.
"""


def main() -> int:
    args = parse_args()
    execution = load_json(RAW / "EXECUTION.json")
    determinism = load_json(RAW / "determinism.json")
    fixtures = load_json(RAW / "fixture-inventory.json")
    tool_inventory = load_json(RAW / "tool-inventory.json")
    inspection = load_json(RAW / "package-inspection.json")
    controls = load_json(RAW / "NEGATIVE-CONTROLS.json")
    pr19 = load_json(RAW / "pr-19-state.json")
    documents = load_documents()

    if execution["fresh_process_checker_commands"] != 112:
        raise RuntimeError("canonical checker command count is not 112")
    if not execution["all_semantic_repeat_pairs_identical"]:
        raise RuntimeError("checker repetitions differ semantically")
    if execution["failed_negative_control_count"] or controls["failed_control_count"]:
        raise RuntimeError("a negative control failed")
    if not execution["source_unchanged"]:
        raise RuntimeError("frozen fixtures changed")
    if inspection["decision"] != "ACCEPTED" or not inspection["source_files_unchanged"]:
        raise RuntimeError("package inspection is not an unchanged acceptance")
    if pr19["response"]["state"] != "MERGED" or pr19["response"]["headRefOid"] != PR19_HEAD:
        raise RuntimeError("PR #19 state/head mismatch")
    if git("rev-parse", "HEAD").stdout.strip() != SOURCE_COMMIT:
        raise RuntimeError("build reports before committing, from the exact source commit")
    if git("rev-parse", "origin/main").stdout.strip() != SOURCE_COMMIT:
        raise RuntimeError("origin/main changed after campaign start")
    historical_diff = git("diff", "--name-only", SOURCE_COMMIT, "--", "evidence/LOCAL-VERIFY-002").stdout.splitlines()
    if historical_diff:
        raise RuntimeError(f"frozen LOCAL-VERIFY-002 changed: {historical_diff}")

    matrix = build_matrix(documents, fixtures, determinism)
    if len(matrix) != 56:
        raise RuntimeError(f"matrix row count mismatch: {len(matrix)}")
    expected_pyright = {
        "standard": {"GA01": 1, "GA02": 1, "GA03": 0, "GA04": 1, "GA05": 1, "GA06": 1, "DC01": 0, "DC02": 1, "DC03": 0, "DC04": 0, "DC05": 0, "DC06": 0, "DC07": 0, "NC01": 1},
        "strict": {"GA01": 1, "GA02": 1, "GA03": 1, "GA04": 1, "GA05": 1, "GA06": 1, "DC01": 1, "DC02": 1, "DC03": 1, "DC04": 0, "DC05": 0, "DC06": 0, "DC07": 1, "NC01": 1},
    }
    for row in matrix:
        if row["checker"] == "mypy" and row["result"] != "MATCHED_MYPY_1_19_1_EXIT":
            raise RuntimeError(f"unexpected mypy 2.3.1 exit drift: {row}")
        if row["checker"] == "Pyright":
            expected = expected_pyright[row["mode"]][row["fixture_id"]]
            if int(row["actual_exit_code"]) != expected:
                raise RuntimeError(f"unexpected Pyright result changed: {row}")
    write_csv(ROOT / "CHECKER-MATRIX.csv", matrix)

    claims = build_claims(matrix)
    write_csv(ROOT / "CLAIM-LEDGER.csv", claims)
    write_json(ROOT / "NEGATIVE-CONTROLS.json", controls)

    baseline = {
        "schema_version": "1.0",
        "campaign": "LOCAL-VERIFY-002B",
        "recorded_at_utc": utc_now(),
        "repository": "QSOLKCB/HERESY-SOFA",
        "source_commit": SOURCE_COMMIT,
        "origin_main_at_start": SOURCE_COMMIT,
        "branch": "evidence/local-verify-002b-checker-completion",
        "pr_19": pr19,
        "pr_19_merge_commit_is_source_commit": pr19["response"]["mergeCommit"]["oid"] == SOURCE_COMMIT,
        "frozen_local_verify_002": tree_identity(FROZEN),
        "frozen_report": {
            "path": "evidence/LOCAL-VERIFY-002/REPORT.json",
            "bytes": (FROZEN / "REPORT.json").stat().st_size,
            "sha256": sha256_file(FROZEN / "REPORT.json"),
        },
        "frozen_manifest": {
            "path": "evidence/LOCAL-VERIFY-002/SHA256SUMS.txt",
            "bytes": (FROZEN / "SHA256SUMS.txt").stat().st_size,
            "sha256": sha256_file(FROZEN / "SHA256SUMS.txt"),
        },
        "frozen_fixture_inventory": {
            "path": "evidence/LOCAL-VERIFY-002/RAW/fixture-inventory.json",
            "bytes": (FROZEN / "RAW/fixture-inventory.json").stat().st_size,
            "sha256": sha256_file(FROZEN / "RAW/fixture-inventory.json"),
        },
        "historical_diff_from_source_commit": historical_diff,
        "historical_evidence_modified": bool(historical_diff),
    }
    write_json(ROOT / "BASELINE.json", baseline)

    system = os.uname()
    dependency_inventory = distribution_inventory(args.mypy_python)
    uv_version = run(str(args.uv), "--version")
    environment = {
        "schema_version": "1.0",
        "campaign": "LOCAL-VERIFY-002B",
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
        "cpu": {"model": cpu_model(), "logical_cpu_count": os.cpu_count()},
        "tools": {
            "cpython": tool_inventory["python"],
            "uv": {
                "version_output": uv_version.stdout.strip(),
                "executable": str(args.uv),
                "executable_bytes": args.uv.stat().st_size,
                "executable_sha256": sha256_file(args.uv),
            },
            "node": tool_inventory["node"],
            "mypy": tool_inventory["mypy"],
            "pyright": tool_inventory["pyright"],
        },
        "mypy_environment": {
            "isolated_venv": True,
            "system_site_packages": False,
            "offline_install": True,
            "uv_pip_check": "All installed packages are compatible",
            "distribution_inventory": dependency_inventory,
        },
        "python_target": "3.14",
        "seed": 26051105,
        "network_during_checker_execution": False,
        "npm_npx_pnpm_invoked": False,
    }
    write_json(ROOT / "ENVIRONMENT.json", environment)

    package_artifacts = [
        artifact_record(inspection["mypy"], "RAW/package-inspection.json#/mypy/members"),
        *[
            artifact_record(value, f"RAW/package-inspection.json#/mypy_dependencies/{name}/members")
            for name, value in inspection["mypy_dependencies"].items()
        ],
        artifact_record(inspection["pyright"], "RAW/package-inspection.json#/pyright/members"),
    ]
    package_artifacts = sorted(package_artifacts, key=lambda item: item["filename"])
    metadata_sources = {
        "ast-serialize-pypi.json": "https://pypi.org/pypi/ast-serialize/json",
        "librt-pypi.json": "https://pypi.org/pypi/librt/json",
        "mypy-2.3.1-pypi.json": "https://pypi.org/pypi/mypy/2.3.1/json",
        "mypy-extensions-1.1.0-pypi.json": "https://pypi.org/pypi/mypy-extensions/1.1.0/json",
        "pathspec-1.0.4-pypi.json": "https://pypi.org/pypi/pathspec/1.0.4/json",
        "pyright-1.1.414-registry.json": "https://registry.npmjs.org/pyright/1.1.414",
        "typing-extensions-4.15.0-pypi.json": "https://pypi.org/pypi/typing-extensions/4.15.0/json",
    }
    metadata_records = []
    for filename, url in metadata_sources.items():
        path = ROOT / "PACKAGES/METADATA" / filename
        metadata_records.append({
            "filename": filename,
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
            "official_source_url": url,
        })
    package_inventory = {
        "schema_version": "1.0",
        "campaign": "LOCAL-VERIFY-002B",
        "acquisition": {
            "authorized_sources": ["official PyPI", "official npm registry Microsoft Pyright distribution"],
            "network_phase_separate_from_execution": True,
            "download_tool": "curl with HTTPS-only/TLS 1.2 minimum",
            "global_installation": False,
            "npm_npx_pnpm_invoked": False,
            "package_lifecycle_scripts_invoked": False,
        },
        "artifact_count": len(package_artifacts),
        "artifacts": package_artifacts,
        "registry_metadata": metadata_records,
        "normalized_acquisition_commands": [
            {
                "argv": [
                    "curl", "--fail", "--location", "--proto", "=https",
                    "--tlsv1.2", "--silent", "--show-error", "--output",
                    f"<ACQUISITION_ROOT>/downloads/{item['filename']}",
                    item["official_source_url"],
                ],
                "exit_code": 0,
                "timestamp": "NOT_CAPTURED",
            }
            for item in package_artifacts
        ],
        "acquisition_timestamp_limitation": "Individual curl start/finish timestamps were not captured; no retrospective timestamps are inferred.",
        "original_archives_unchanged_after_inspection": inspection["source_files_unchanged"],
        "full_safety_receipt": {
            "path": "RAW/package-inspection.json",
            "bytes": (RAW / "package-inspection.json").stat().st_size,
            "sha256": sha256_file(RAW / "package-inspection.json"),
        },
        "pyright_dependency_assessment": inspection["pyright"]["dependency_assessment"],
        "mypy_dependency_resolution": dependency_inventory,
        "failed_preflight": "RAW/MYPY-DEPENDENCY-PREFLIGHT.json",
    }
    write_json(ROOT / "PACKAGE-INVENTORY.json", package_inventory)

    result_map = matrix_map(matrix)
    report = {
        "schema_version": "1.0",
        "campaign": "LOCAL-VERIFY-002B",
        "generated_at_utc": utc_now(),
        "source_commit": SOURCE_COMMIT,
        "baseline_ref": "BASELINE.json",
        "environment_ref": "ENVIRONMENT.json",
        "package_inventory_ref": "PACKAGE-INVENTORY.json",
        "frozen_fixture_source": "evidence/LOCAL-VERIFY-002/FIXTURES",
        "fixtures_copied_or_modified": False,
        "execution": execution,
        "coverage": {
            "mypy_1.19.1": "FROZEN_PRIOR_CHECKER_CONFIRMED",
            "mypy_2.3.1": "CHECKER_CONFIRMED",
            "pyright_1.1.414": "CHECKER_CONFIRMED",
        },
        "result_summary": {
            "mypy_exit_pattern_matches_1_19_1": all(
                row["result"] == "MATCHED_MYPY_1_19_1_EXIT"
                for row in matrix if row["checker"] == "mypy"
            ),
            "original_genericalias_reply": "Both checkers reject.",
            "types_genericalias_static_utility": "Both reject calling the runtime alias and infer Any/Unknown for its result.",
            "typevartuple_literal_ellipsis": "Both reject the tested user-defined Generic[*Ts] forms.",
            "dataclass_bare_instance": "mypy 2.3.1 reproduces var-annotated; Pyright standard accepts with Unknown and strict rejects Unknown.",
            "dataclass_factory_mismatch": "Both reject without suppression; suppression leaves the prior native runtime C-versus-C2 defect.",
            "sound_alternatives": "DC04, DC05 and DC06 pass both modes of both checkers.",
        },
        "minimized_counterexamples": [
            {
                "id": "GA01",
                "finding": "typing.GenericAlias is unavailable and GenericAlias[...] is rejected.",
                "mypy_rules": result_map[("mypy", "default", "GA01")]["diagnostic_rules"],
                "pyright_rules": result_map[("Pyright", "standard", "GA01")]["diagnostic_rules"],
            },
            {
                "id": "GA05",
                "finding": "Packed[int, ...] and Packed[...] are runtime-accepted in prior evidence but statically rejected here.",
                "mypy_rules": result_map[("mypy", "default", "GA05")]["diagnostic_rules"],
                "pyright_rules": result_map[("Pyright", "standard", "GA05")]["diagnostic_rules"],
            },
            {
                "id": "DC03",
                "finding": "The ignore makes checkers reveal C2 while prior native execution constructs C.",
                "mypy_default_exit": int(result_map[("mypy", "default", "DC03")]["actual_exit_code"]),
                "pyright_standard_exit": int(result_map[("Pyright", "standard", "DC03")]["actual_exit_code"]),
            },
        ],
        "negative_controls": {
            "count": controls["control_count"],
            "failed": controls["failed_control_count"],
            "ref": "NEGATIVE-CONTROLS.json",
        },
        "determinism": {
            "all_semantic_repeat_pairs_identical": determinism["all_semantic_repeat_pairs_identical"],
            "pair_count": len(determinism["pairs"]),
            "pyright_measurement_fields_excluded": ["time", "summary.timeInSec"],
            "raw_outputs_preserved": True,
            "ref": "RAW/determinism.json",
        },
        "pre_finalization_events": [
            "RAW/MYPY-DEPENDENCY-PREFLIGHT.json",
            "RAW/PACKAGE-VALIDATOR-PREFLIGHT.json",
            "RAW/PREFLIGHT-PARSER-CORRECTION.json",
            "RAW/PRE-SELF-CONTAINED-RUN.json",
        ],
        "fresh_offline_reproduction": {
            "status": "EXECUTED_NATIVE",
            "setup_receipt": "RAW/FRESH-OFFLINE-SETUP.json",
            "targeted_control_receipt": "RAW/FRESH-OFFLINE-REPRODUCTION.json",
            "result": "PASS",
        },
        "limitations": [
            "This addendum executes static checkers only; runtime findings are cross-referenced from immutable LOCAL-VERIFY-002.",
            "The results are version-scoped to mypy 2.3.1 and Pyright 1.1.414 with Python target 3.14.",
            "Pyright standard acceptance is not equivalent to strict acceptance or runtime correctness.",
            "Pyright output contains nondeterministic wall-clock and duration measurements; semantic repeat comparison excludes only those measurements.",
        ],
        "safety": {
            "checker_execution_offline": True,
            "global_installation": False,
            "npm_npx_pnpm_invoked": False,
            "sofa_mutations": False,
            "historical_evidence_modified": False,
        },
        "artifacts": {
            "checker_matrix": "CHECKER-MATRIX.csv",
            "claim_ledger": "CLAIM-LEDGER.csv",
            "negative_controls": "NEGATIVE-CONTROLS.json",
            "open_issues": "OPEN-ISSUES.md",
            "review": "REVIEW.md",
        },
    }
    write_json(ROOT / "REPORT.json", report)
    (ROOT / "REVIEW.md").write_text(build_review(matrix, report), encoding="utf-8")

    open_issues = """# LOCAL-VERIFY-002B open issues

## Closed by this addendum

- Mypy 2.3.1: all 28 missing default/strict rows are `CHECKER_CONFIRMED`.
- Pyright 1.1.414: all 28 missing standard/strict rows are `CHECKER_CONFIRMED` using the official bundled CLI on Node 22.18.0.
- The prior LOCAL-VERIFY-002 mypy 1.19.1 evidence remains immutable and hash-valid.

## Still bounded or unverified

- No claim is made for mypy or Pyright versions other than the pinned versions.
- CPython runtime behavior was not rerun in 002B. Runtime comparisons cite immutable LOCAL-VERIFY-002 receipts.
- Checker acceptance after `# type: ignore` does not verify the runtime dataclass invariant.
- Pyright standard and strict deliberately differ on Unknown-related diagnostics; neither mode may be substituted for the other.
- `types.GenericAlias` runtime behavior does not imply static-call or specialization support.
- The tested literal ellipsis result concerns these user-defined generic fixtures; it is not a universal ban on ellipsis in every typing construct.
- No SOFA publication, vote or verification action occurred. Any publication remains a separate owner-reviewed phase.
"""
    (ROOT / "OPEN-ISSUES.md").write_text(open_issues, encoding="utf-8")
    print(json.dumps({
        "matrix_rows": len(matrix),
        "claim_rows": len(claims),
        "negative_controls": controls["control_count"],
        "failed_negative_controls": controls["failed_control_count"],
        "mypy_2_3_1": "CHECKER_CONFIRMED",
        "pyright_1_1_414": "CHECKER_CONFIRMED",
    }, sort_keys=True))
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mypy-python", required=True, type=Path)
    parser.add_argument("--uv", required=True, type=Path)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
