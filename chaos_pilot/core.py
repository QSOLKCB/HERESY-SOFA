"""Offline triage and evidence: no imports of network clients or subprocess.

Findings are candidate patterns needing human review, NOT vulnerabilities.
"""
import hashlib
import json
import re
from pathlib import Path

CASES = Path(__file__).with_name("cases.json")
SCOPE = {
    "QSOLKCB/HERESY-SOFA": "4faf7bfb5b2ff6e27d95756ec3e081f75e3e7239",
    "QSOLKCB/PROVENANCE": "2db834540e2f585ceda3be7ff7e46286c15d8b6c",
    "QSOLKCB/QSOL-IBAE": "2f9c3e826ee177a75cf12ca0eeb7d5a97070cff9",
}


def cases():
    data = json.loads(CASES.read_text(encoding="utf-8"))
    if data["schema_version"] != 1:
        raise ValueError("unsupported case manifest")
    ids = [x["id"] for x in data["cases"]]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate incident IDs")
    for case in data["cases"]:
        if any(repo not in SCOPE for repo in case["comparison_repositories"]):
            raise ValueError("case contains out-of-scope repo")
    return data["cases"]


def candidate_workflow_flags(text):
    """Deliberately conservative heuristic, not a YAML parser or security verdict.

    Does NOT execute workflow content. Lower confidence flags require human review.
    """
    flags = []
    if re.search(r"(?m)^\s*pull_request_target\s*:", text):
        flags.append("privileged_pr_trigger_review")
    if "github.event.pull_request.head.sha" in text or "github.event.pull_request.head.repo" in text:
        flags.append("untrusted_pr_ref_review")
    if re.search(r"(?m)^\s*(?:-\s*)?run\s*:\s*.*\$\{\{\s*github\.event\.", text):
        flags.append("expression_in_run_line_review")
    if re.search(r"(?m)^\s*(curl|wget)\b", text) and re.search(r"\|\s*(sh|bash)\b", text):
        flags.append("remote_script_execution_review")
    return sorted(set(flags))


def compare_snapshot(repo, sha, relative_path, text):
    """Inspect a caller-supplied public snapshot only; do not fetch code here."""
    if repo not in SCOPE or SCOPE[repo] != sha:
        raise ValueError("repository and exact SHA must match approved scope")
    path = Path(relative_path)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ValueError("unsafe relative path")
    encoded = text.encode("utf-8")
    if len(encoded) > 256_000:
        raise ValueError("snapshot too large")
    return {
        "schema_version": 1,
        "status": "review_candidate_not_vulnerability",
        "repository": repo,
        "source_sha": sha,
        "relative_path": str(path),
        "sha256": hashlib.sha256(encoded).hexdigest(),
        "flags": candidate_workflow_flags(text) if path.suffix in {".yml", ".yaml"} else [],
        "limitations": "Text heuristics only. No YAML semantics, execution, network or exploit testing.",
    }


def validate_receipt(receipt, approved_repos=SCOPE):
    if not isinstance(receipt, dict) or receipt.get("schema_version") != 1:
        raise ValueError("receipt schema mismatch")
    repo, sha = receipt.get("repository"), receipt.get("source_sha")
    if repo not in approved_repos or sha != approved_repos[repo]:
        raise ValueError("receipt outside pinned scope")
    if receipt.get("status") != "review_candidate_not_vulnerability":
        raise ValueError("invalid evidence state")
    if not isinstance(receipt.get("flags"), list) or any(not isinstance(v, str) for v in receipt["flags"]):
        raise ValueError("invalid flags")
    digest = receipt.get("sha256", "")
    if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise ValueError("invalid hash")
    return True