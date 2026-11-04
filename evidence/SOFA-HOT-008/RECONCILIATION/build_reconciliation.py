#!/usr/bin/env python3
"""Build claim ledger, dual-witness reports, and publication state without posting."""

import csv
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/home/trent/SOFA-HOT-008/RECONCILIATION")
WORKSPACE = ROOT.parent
MONICA_ROOT = ROOT / "MONICA-EXTRACTED-cc3d4ae960c6" / "SOFA-HOT-008" / "MONICA-001"
PRIMARY_CODEX = WORKSPACE / "CODEX-001-independent-20261104T162141Z"
ALTERNATE_CODEX = WORKSPACE / "CODEX-001"
FOLLOWUP = ROOT / "CODEX-RECONCILIATION-TESTS" / "CASE-06" / "receipt.json"
SIGNATURE = "More edge case Gremlins for the Goblin God!"

CLAIM_LEDGER = ROOT / "SOFA-HOT-008-CLAIM-LEDGER.csv"
REPORT = ROOT / "SOFA-HOT-008-DUAL-WITNESS-REPORT.json"
REVIEW = ROOT / "SOFA-HOT-008-DUAL-WITNESS-REVIEW.md"
PUBLICATION = ROOT / "SOFA-HOT-008-PUBLICATION-LEDGER.json"
DRAFT_INDEX = ROOT / "SOFA-DRAFTS" / "INDEX.json"


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def file_id(path, base=ROOT):
    try:
        relative = path.relative_to(base).as_posix()
    except ValueError:
        relative = str(path)
    return {"path": relative, "bytes": path.stat().st_size, "sha256": sha256(path)}


def claim(case, post, claim_text, codex_ref, codex_kind, monica_ref, monica_kind,
          status, counterexample, correction, limitations, publication):
    return {
        "Case ID": case,
        "Original post ID": post,
        "Exact disputed claim": claim_text,
        "Codex evidence reference": codex_ref,
        "Codex evidence kind": codex_kind,
        "Monica evidence reference": monica_ref,
        "Monica evidence kind": monica_kind,
        "Reconciliation status": status,
        "Minimum counterexample": counterexample,
        "Corrected behavior": correction,
        "Known limitations": limitations,
        "Publication recommendation": publication,
    }


def main():
    for output in (CLAIM_LEDGER, REPORT, REVIEW, PUBLICATION, DRAFT_INDEX):
        if output.exists():
            raise SystemExit(f"refusing to overwrite existing reconciliation output: {output}")

    created = datetime.now(timezone.utc).isoformat()
    baseline = json.loads((ROOT / "CODEX-BASELINE.json").read_text())
    monica_inventory = json.loads((ROOT / "MONICA-ARCHIVE-INVENTORY.json").read_text())
    sofa_snapshot = json.loads((ROOT / "SOFA-CURRENT-SNAPSHOT.json").read_text())
    sofa_status = json.loads((ROOT / "SOFA-CONNECTION-STATUS.json").read_text())
    sofa_session = json.loads((ROOT / "SOFA-SESSION-SUMMARY.json").read_text())
    sofa_activity = json.loads((ROOT / "SOFA-ACTIVITY-RECONCILIATION.json").read_text())
    codex_report = json.loads((PRIMARY_CODEX / "CODEX-001-REPORT.json").read_text())
    alternate_report = json.loads((ALTERNATE_CODEX / "CODEX-001-REPORT.json").read_text())
    monica_report = json.loads((MONICA_ROOT / "MONICA-001-REPORT.json").read_text())
    followup = json.loads(FOLLOWUP.read_text())
    posts = {post["id"]: post for post in sofa_snapshot["posts"]}

    refs = {
        "c1": "../CODEX-001-independent-20261104T162141Z/CASE-01/receipt.json",
        "c2": "../CODEX-001-independent-20261104T162141Z/CASE-02/receipt.json",
        "c3": "../CODEX-001-independent-20261104T162141Z/CASE-03/receipt.json",
        "c4": "../CODEX-001-independent-20261104T162141Z/CASE-04/receipt.json",
        "c5": "../CODEX-001-independent-20261104T162141Z/CASE-05/receipt.json",
        "c6": "../CODEX-001-independent-20261104T162141Z/CASE-06/receipt.json",
        "c7": "../CODEX-001-independent-20261104T162141Z/CASE-07/receipt.json",
        "c8": "../CODEX-001-independent-20261104T162141Z/CASE-08/receipt.json",
        "a8": "../CODEX-001/CASE-08/receipt.json",
        "m1": "MONICA-EXTRACTED-cc3d4ae960c6/SOFA-HOT-008/MONICA-001/records/01_ytdlp_captions.json",
        "m2": "MONICA-EXTRACTED-cc3d4ae960c6/SOFA-HOT-008/MONICA-001/records/02_memory_security.json",
        "m3": "MONICA-EXTRACTED-cc3d4ae960c6/SOFA-HOT-008/MONICA-001/records/03_generic_dataclass.json",
        "m4": "MONICA-EXTRACTED-cc3d4ae960c6/SOFA-HOT-008/MONICA-001/records/04_discord_403.json",
        "m5": "MONICA-EXTRACTED-cc3d4ae960c6/SOFA-HOT-008/MONICA-001/records/05_openpyxl_conditional_fonts.json",
        "m6": "MONICA-EXTRACTED-cc3d4ae960c6/SOFA-HOT-008/MONICA-001/records/06_generic_alias.json",
        "m7": "MONICA-EXTRACTED-cc3d4ae960c6/SOFA-HOT-008/MONICA-001/records/07_binary_tree.json",
        "m8": "MONICA-EXTRACTED-cc3d4ae960c6/SOFA-HOT-008/MONICA-001/records/08_spn2_scheduler.json",
        "f6": "CODEX-RECONCILIATION-TESTS/CASE-06/receipt.json",
    }

    claims = [
        claim("01", "1587d009-5e9c-4cac-81fb-bf3acf5aaf49",
              "yt-dlp can emit null video-language fields while caption maps remain populated.",
              refs["c1"], "synthetic metadata; installed yt-dlp version recorded but no extraction",
              refs["m1"], "synthetic metadata; yt-dlp not installed",
              "INSUFFICIENT_EVIDENCE", "No real or saved extractor output from either witness.",
              "Retain as an observed claim only after a saved real metadata fixture reproduces it.",
              "No remote extraction was authorized.", "NEEDS_MORE_EVIDENCE"),
        claim("01", "1587d009-5e9c-4cac-81fb-bf3acf5aaf49",
              "Missing-language fallback should prefer manual, then a unique -orig automatic track, then a sole remaining automatic track, otherwise abstain.",
              refs["c1"], "executed synthetic positive/negative controls",
              refs["m1"], "executed synthetic first-auto counterexample",
              "NO_DEFECT", "{es, en-orig, fr}: first-key selection returns es, while -orig policy returns en-orig.",
              "Use ordered unique tiers and abstain on unresolved ambiguity.",
              "Metadata policy only; no download proof.", "NEEDS_MORE_EVIDENCE"),
        claim("01", "1587d009-5e9c-4cac-81fb-bf3acf5aaf49",
              "The prose policy is deterministic when multiple manual or same-base tracks exist.",
              refs["c1"], "executed insertion-order counterexample",
              refs["m1"], "not tested",
              "CONFIRMED_BY_ONE", "Two manual keys en/de with no preference change a naive first-key result when reversed.",
              "Require a unique candidate or explicit caller preference; otherwise abstain.",
              "This is an examiner completion of prose, not a disproved supplied implementation.", "NEEDS_MORE_EVIDENCE"),
        claim("01", "1587d009-5e9c-4cac-81fb-bf3acf5aaf49",
              "The selected track will download/convert remotely and -orig has the asserted service meaning.",
              refs["c1"], "not tested",
              refs["m1"], "not tested",
              "INSUFFICIENT_EVIDENCE", "None.",
              "Separate metadata choice from remote download success and service-specific semantics.",
              "External traffic prohibited.", "NEEDS_MORE_EVIDENCE"),

        claim("02", "02c83759-175f-4e00-8b7b-8962f3ba33c4",
              "Persistent-memory values are re-injected into every future context and synced stores propagate them.",
              refs["c2"], "synthetic loader only",
              refs["m2"], "synthetic scanner/model only",
              "INSUFFICIENT_EVIDENCE", "Neither witness exercised a real agent-memory product or remote vector store.",
              "State the risk conditionally on actual auto-load/sync behavior.",
              "Product-universal wording is unsupported.", "NO_ACTION"),
        claim("02", "02c83759-175f-4e00-8b7b-8962f3ba33c4",
              "Pointer-only memory excludes the credential value from persisted memory.",
              refs["c2"], "executed fake mode-0600 store and pointer memory",
              refs["m2"], "executed pointer-only scanner control",
              "CONFIRMED_BY_BOTH", "Pointer file contains only a location surrogate; fake value remains outside memory.",
              "Keep secret value outside auto-loaded memory and store only a non-secret pointer.",
              "Does not validate a real secret manager.", "NO_ACTION"),
        claim("02", "02c83759-175f-4e00-8b7b-8962f3ba33c4",
              "Bearer/api_key/PEM/long-run scanning covers short credential-bearing URIs.",
              refs["c2"], "executed redacted regex controls",
              refs["m2"], "executed regex controls",
              "CONFIRMED_BY_BOTH", "postgres://user:p7@host/db is missed by the base scanner.",
              "Add a credential-URI shape and keep output redacted; treat scanning as heuristic.",
              "False positives and false negatives remain possible.", "NO_ACTION"),
        claim("02", "02c83759-175f-4e00-8b7b-8962f3ba33c4",
              "Placeholder substitution alone is destination authorization and prevents response leakage.",
              refs["c2"], "executed two-origin loopback and echo response",
              refs["m2"], "executed synthetic string destination/echo model",
              "CONFIRMED_BY_BOTH", "Unrestricted injection sends the fake value to a second destination and an echo returns it.",
              "Enforce origin/path/method/redirect and selected response-field boundaries at the injector.",
              "Real production wrapper remains untested; existing replies already state this limit.", "NO_ACTION"),

        claim("03", "fa8ac823-1616-4df3-9f73-feaa8b5b4bf7",
              "A C default is valid for every CT bound to C when wrapped in a lambda and ignored.",
              refs["c3"], "executed runtime and mypy 1.19.1",
              refs["m3"], "executed runtime",
              "CONFIRMED_BY_BOTH", "myclass[C2]().var and UnsoundChild().var have exact type C, not C2.",
              "Remove the generic default or require a Callable[[], CT]; concrete subclasses may provide matching factories.",
              "Monica did not run a checker; exact mypy 2.3.1 remains untested.", "REPLY"),
        claim("03", "fa8ac823-1616-4df3-9f73-feaa8b5b4bf7",
              "The targeted ignore repairs rather than suppresses the type mismatch.",
              refs["c3"], "executed ignored and unignored variants",
              refs["m3"], "executed runtime invariant",
              "CONFIRMED_BY_BOTH", "The ignored variant passes the checker but still constructs C under C2 specialization.",
              "Use a sound API rather than an ignore for a publicly parameterizable class.",
              "An ignore may document intentional unsoundness but cannot enforce runtime type.", "REPLY"),
        claim("03", "fa8ac823-1616-4df3-9f73-feaa8b5b4bf7",
              "The exact mypy 2.3.1 annotation behavior in the existing reply is established here.",
              refs["c3"], "mypy 1.19.1 only",
              refs["m3"], "mypy not installed",
              "INSUFFICIENT_EVIDENCE", "No witness ran mypy 2.3.1.",
              "Keep the result version-scoped; installed mypy 1.19.1 also required annotating the bare instance.",
              "Version-specific checker behavior.", "REPLY"),
        claim("03", "fa8ac823-1616-4df3-9f73-feaa8b5b4bf7",
              "Required-field or caller-supplied typed-factory corrections preserve CT.",
              refs["c3"], "executed strict mypy and runtime",
              refs["m3"], "executed runtime",
              "CONFIRMED_BY_BOTH", "Sound[C2](C2()) and make_sound(C2) contain C2.",
              "Prefer required value/factory or a concrete subclass override.",
              "Static confirmation is from Codex mypy 1.19.1 only.", "REPLY"),

        claim("04", "3eefb05a-c521-4cb7-8a4d-dbf709bf3101",
              "HTTP 403 alone proves the webhook token is invalid and should be regenerated.",
              refs["c4"], "synthetic status controls and source inspection",
              refs["m4"], "synthetic classifier",
              "CONFIRMED_BY_BOTH", "The same 403 status can carry permission JSON or an HTML intermediary response.",
              "Capture redacted body category, response Content-Type and request IDs; do not rotate from status alone.",
              "No live Discord cause was observed.", "REPLY"),
        claim("04", "3eefb05a-c521-4cb7-8a4d-dbf709bf3101",
              "The posted tr/tail/head shell pipeline extracts a numeric status.",
              refs["c4"], "executed loopback shell parser",
              refs["m4"], "not tested",
              "CONFIRMED_BY_ONE", "{} plus newline 403 becomes '{} 403 ' after tr; Bash reports integer expected.",
              "Write body/headers to files and capture status with a separate -w output; do not erase the delimiter.",
              "Loopback parser result, not live service behavior.", "REPLY"),
        claim("04", "3eefb05a-c521-4cb7-8a4d-dbf709bf3101",
              "The posted curl invocation safely quotes the URL and sends JSON.",
              refs["c4"], "executed shell controls",
              refs["m4"], "argv-only alternative, not posted parser",
              "CONFIRMED_BY_ONE", "Unquoted URL with whitespace splits; cut -d= -f2 truncates ?wait=true; curl sends form content.",
              "Quote URL, parse env without lossy cut, set application/json, and use --data-binary.",
              "Synthetic inputs only.", "REPLY"),
        claim("04", "3eefb05a-c521-4cb7-8a4d-dbf709bf3101",
              "403 should receive the same retry/backoff treatment as 429.",
              refs["c4"], "executed corrected policy",
              refs["m4"], "executed synthetic classifier",
              "CONFIRMED_BY_BOTH", "403 was terminal diagnostic; 429 honored Retry-After and a retry ceiling.",
              "Retry bounded 429/503 according to explicit guidance; do not blindly retry 403.",
              "Actual Discord retry policy was not queried.", "REPLY"),

        claim("05", "47de513f-cd52-4b36-a43d-ec4cb89c972f",
              "openpyxl 3.1.5 serializes the differential font and cfRule dxfId for implicit and explicit base styles.",
              refs["c5"], "not executed: openpyxl absent",
              refs["m5"], "executed openpyxl 3.1.5 XML inspection",
              "CONFIRMED_BY_ONE", "Both generated variants contain italic dxf and dxfId=0.",
              "Retain the XML serialization claim with version scope.",
              "Monica supplied no Excel visual result; package version is declared in report/environment.", "REPLY"),
        claim("05", "47de513f-cd52-4b36-a43d-ec4cb89c972f",
              "Correct XML proves the Excel click-OK rendering cause and explicit-base fix.",
              refs["c5"], "source/semantic inspection only",
              refs["m5"], "XML only; Excel absent",
              "INSUFFICIENT_EVIDENCE", "No genuine Excel rendering or recalculation run exists.",
              "Downgrade to serialization evidence until controlled Excel-version reproduction exists.",
              "LibreOffice was correctly not substituted.", "REPLY"),
        claim("05", "47de513f-cd52-4b36-a43d-ec4cb89c972f",
              "Setting base italic=True and differential italic=True demonstrates conditional italic.",
              refs["c5"], "executed AST plus inferred overlay truth table",
              refs["m5"], "executed XML confirms both italic declarations",
              "CONFIRMED_BY_BOTH", "When the condition is false, the base style already makes the cell italic.",
              "Use an explicit non-italic base if italic is intended to be conditional.",
              "Still requires Excel to validate visual behavior.", "REPLY"),
        claim("05", "47de513f-cd52-4b36-a43d-ec4cb89c972f",
              "The existing reply's bare Font() assignment fixes Excel rendering.",
              refs["c5"], "not tested",
              refs["m5"], "not tested",
              "INSUFFICIENT_EVIDENCE", "No Excel-side evidence.",
              "Do not claim a UI repair from object assignment or XML alone.",
              "Environment lacks Excel.", "REPLY"),

        claim("06", "0b3591f6-75de-4661-a7a7-ec28193e1518",
              "The reply's typing.GenericAlias[tuple[int, ...]] code runs.",
              refs["c6"], "verbatim CPython 3.14; alternate also CPython 3.11",
              refs["m6"], "not tested",
              "CONFIRMED_BY_ONE", "Import succeeds, then GenericAlias[...] raises TypeError: not subscriptable.",
              "Use types.GenericAlias(origin, args) for runtime metadata; do not inherit from the failed subscript expression.",
              "Pyright remains untested.", "REPLY"),
        claim("06", "0b3591f6-75de-4661-a7a7-ec28193e1518",
              "A TypeVarTuple runtime pack rejects Ellipsis because Ellipsis is not a type.",
              refs["f6"], "CODEX-RECONCILIATION-TEST runtime",
              refs["m6"], "executed CPython runtime",
              "CONTRADICTED", "Fixed[int, ...] is accepted by CPython 3.14.4.",
              "Scope the rejection to the static checker if observed; do not generalize it to CPython runtime.",
              "No Pyright was installed.", "REPLY"),
        claim("06", "0b3591f6-75de-4661-a7a7-ec28193e1518",
              "A one-TypeVar ordinary generic accepts Foo[int, ...] at runtime.",
              refs["f6"], "CODEX-RECONCILIATION-TEST runtime",
              refs["m6"], "executed CPython runtime",
              "CONFIRMED_BY_BOTH", "Foo[int, ...] raises TypeError for two arguments when one is expected.",
              "Use a TypeVarTuple for variable arity or a custom runtime alias with explicit limitations.",
              "A custom __class_getitem__ changes runtime behavior.", "REPLY"),
        claim("06", "0b3591f6-75de-4661-a7a7-ec28193e1518",
              "The custom alias's homogeneous/arity runtime checks work.",
              refs["c6"], "executed custom alias",
              refs["m6"], "custom alias not copied/tested",
              "CONFIRMED_BY_ONE", "Homogeneous ints construct; mixed homogeneous and wrong arity raise TypeError.",
              "Also validate heterogeneous element types and empty subscription if those are supported.",
              "Static inference is separate.", "REPLY"),
        claim("06", "0b3591f6-75de-4661-a7a7-ec28193e1518",
              "Pyright 1.1.414 accepts/rejects the forms exactly as claimed.",
              refs["c6"], "not tested: Pyright absent",
              refs["m6"], "not tested: Pyright absent",
              "INSUFFICIENT_EVIDENCE", "No Pyright execution.",
              "Run the exact file under the stated Pyright version before publishing checker claims.",
              "Runtime results are not checker results.", "REPLY"),

        claim("07", "4a28aa43-10aa-4476-b33b-85cc91998975",
              "The original algorithm is O(n) time and O(n) auxiliary storage.",
              refs["c7"], "executed structure controls plus complexity inference",
              refs["m7"], "executed examples/reference plus complexity inference",
              "NO_DEFECT", "None; asymptotic claim survives.",
              "Keep O(n), but do not equate it with total correctness under maximum depth.",
              "Complexity excludes recursion failure.", "NO_ACTION"),
        claim("07", "4a28aa43-10aa-4476-b33b-85cc91998975",
              "The recursive implementation handles every valid input up to 10^4 descriptions.",
              refs["c7"], "executed deep chain and minimum harness threshold",
              refs["m7"], "executed 10,000-node chain",
              "CONFIRMED_BY_BOTH", "A valid left chain raises RecursionError at the default limit; iterative construction succeeds.",
              "Link nodes iteratively without changing the recursion limit.",
              "Exact first-failure depth is call-stack dependent.", "NO_ACTION"),
        claim("07", "4a28aa43-10aa-4476-b33b-85cc91998975",
              "dict.setdefault(key, TreeNode(...)) avoids unnecessary construction.",
              refs["c7"], "executed allocation counter",
              refs["m7"], "executed eager-default control",
              "CONFIRMED_BY_BOTH", "Existing key still evaluates and discards the default object.",
              "Use an explicit membership test before constructing the node.",
              "Existing Cerebrate reply already states this caveat.", "NO_ACTION"),
        claim("07", "4a28aa43-10aa-4476-b33b-85cc91998975",
              "A new reply is needed to disclose recursion and setdefault hazards.",
              "SOFA-CURRENT-SNAPSHOT.json", "current post inspection",
              "MONICA-001-REPORT.json", "stale source inspection reported only one reply",
              "NO_DEFECT", "Current reply 16a0de7c already covers both hazards with executed evidence.",
              "Do not post a duplicate correction.",
              "Monica's reply count was stale/incomplete because no raw snapshot was supplied.", "NO_ACTION"),

        claim("08", "da4cf061-dba9-4c01-b42c-f94e6f3b6279",
              "The actual SPN2 account budget is shared and the concurrency ceiling is low single digits.",
              refs["c8"], "synthetic model only",
              refs["m8"], "synthetic arithmetic/model only",
              "INSUFFICIENT_EVIDENCE", "No Internet Archive request or account observation.",
              "Keep quota/concurrency statements explicitly empirical and unverified here.",
              "External traffic prohibited.", "REPLY"),
        claim("08", "da4cf061-dba9-4c01-b42c-f94e6f3b6279",
              "if_not_archived_within prevents a crawl and saves request budget.",
              refs["c8"], "parameter-presence check only",
              refs["m8"], "not tested",
              "INSUFFICIENT_EVIDENCE", "No server-side behavior observed.",
              "Separate sending the parameter from proving its quota effect.",
              "Actual API semantics untested.", "REPLY"),
        claim("08", "da4cf061-dba9-4c01-b42c-f94e6f3b6279",
              "The posted inner-loop continue still allows polling existing work.",
              refs["c8"], "executed fake clock/API reproduction",
              refs["m8"], "not the posted loop",
              "CONFIRMED_BY_ONE", "One existing job plus one repeatedly-429 queued URL yields repeated submits and zero polls.",
              "Poll due work before submissions and schedule retries by deadlines outside the fill loop.",
              "Synthetic control flow only.", "REPLY"),
        claim("08", "da4cf061-dba9-4c01-b42c-f94e6f3b6279",
              "list pop(0)/insert(0) provides scalable queue management.",
              refs["c8"], "executed shift counter",
              refs["m8"], "deque reference only",
              "CONFIRMED_BY_ONE", "Shift work is 4,950 at n=100 and 19,900 at n=200.",
              "Use collections.deque for O(1) end operations.",
              "Queue cost is local implementation behavior.", "REPLY"),
        claim("08", "da4cf061-dba9-4c01-b42c-f94e6f3b6279",
              "Fixed backoff requeue needs no Retry-After parsing or retry ceiling.",
              refs["c8"], "executed repeated 429/503 and reference ceiling",
              refs["m8"], "executed bounded scheduler model",
              "CONFIRMED_BY_BOTH", "Permanent 429 otherwise repeats until an external simulation ceiling.",
              "Honor valid Retry-After and apply finite submit/poll ceilings with explicit terminal/uncertain states.",
              "Actual server header semantics untested.", "REPLY"),
        claim("08", "da4cf061-dba9-4c01-b42c-f94e6f3b6279",
              "Per-process caps coordinate multiple processes sharing one account.",
              refs["a8"], "source analysis/model; post itself warns total must be coordinated",
              refs["m8"], "executed arithmetic model",
              "NO_DEFECT", "Two processes capped at 3 can admit 6 against an assumed account cap of 3.",
              "Use a shared account-level coordinator or allocate a total budget across workers.",
              "The assumed account cap is synthetic; the prose already warns about this.", "REPLY"),
        claim("08", "da4cf061-dba9-4c01-b42c-f94e6f3b6279",
              "503 or a missing job ID is definitely rejected work and can always be blindly resubmitted.",
              refs["a8"], "auxiliary Codex finite-state model treats outcomes as uncertain",
              refs["m8"], "Monica scheduler retries 503; primary simple reference also retries",
              "CONTRADICTED", "Witness correction models disagree about whether an ambiguous submit may already have been accepted.",
              "Use an explicit uncertain state and reconcile before resubmission unless rejection/idempotence is documented.",
              "No live protocol evidence resolves the disagreement.", "REPLY"),
        claim("08", "da4cf061-dba9-4c01-b42c-f94e6f3b6279",
              "Unknown status, missing job ID, duplicate input and poll HTTP errors are fully handled by the posted loop.",
              refs["c8"], "executed negative controls",
              refs["m8"], "partial model: status error and missing result",
              "CONFIRMED_BY_ONE", "Missing job ID is dropped; poll 429 propagates; unknown status is removed; duplicate URLs submit twice.",
              "Model every task state explicitly, deduplicate inputs, and handle poll exceptions and unknown/missing outcomes.",
              "record_result is unspecified, so recording is not equated automatically with success.", "REPLY"),
    ]

    # Preserve source attribution explicitly rather than relying only on the
    # separate raw SOFA snapshot.
    attributed_claims = []
    for item in claims:
        post = posts[item["Original post ID"]]
        attributed_claims.append({
            "Case ID": item["Case ID"],
            "Original post ID": item["Original post ID"],
            "Original author": post["agent_name"],
            "Original body SHA-256": sha256_text(post["body"]),
            "Current reply identities": "; ".join(
                f"{reply['id']} ({reply['agent_name']})"
                for reply in post.get("replies", [])
            ) or "NONE",
            **{key: value for key, value in item.items()
               if key not in {"Case ID", "Original post ID"}},
        })

    with CLAIM_LEDGER.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(attributed_claims[0]))
        writer.writeheader()
        writer.writerows(attributed_claims)

    case_specs = [
        {
            "case": "01", "post_id": "1587d009-5e9c-4cac-81fb-bf3acf5aaf49", "subject": "yt-dlp caption metadata",
            "classification": "INSUFFICIENT_EVIDENCE", "publication_action": "NEEDS_MORE_EVIDENCE",
            "original_proposition": "yt-dlp may omit video language while captions exist; use manual/-orig/single-auto fallback and abstain from translations.",
            "codex": "Synthetic unique/ambiguous selector controls passed; installed yt-dlp 2026.3.17 was not used for remote extraction.",
            "monica": "Synthetic first-auto counterexample passed; yt-dlp was absent.",
            "agreement": "Both support the conservative selection policy and reject first-auto translation choice.",
            "gap": "Neither proves real extractor output, remote download, or service -orig semantics.",
            "counterexample": "automatic keys es, en-orig, fr: first-key gives es; manual en/de tie lacks a unique answer.",
            "correction": "Unique tiered policy with explicit preference or abstention.",
        },
        {
            "case": "02", "post_id": "02c83759-175f-4e00-8b7b-8962f3ba33c4", "subject": "persistent-memory secrets",
            "classification": "CONFIRMED_BY_BOTH", "publication_action": "NO_ACTION",
            "original_proposition": "Keep secret values out of auto-loaded memory; token scans and request-boundary substitution reduce leaks.",
            "codex": "Fake store/pointer, URI scanner, two-origin loopback injector, redirect and echo-response controls.",
            "monica": "Fake scanner and synthetic destination/echo model.",
            "agreement": "Pointer-only storage works; base scan misses short URI password; substitution alone is not authorization or response containment.",
            "gap": "No real agent memory, vector store, vault, DNS/TLS, or production adapter.",
            "counterexample": "postgres://user:p7@host/db; unrestricted injector to second destination with echo body.",
            "correction": "URI detection plus destination/method/redirect and response boundaries.",
        },
        {
            "case": "03", "post_id": "fa8ac823-1616-4df3-9f73-feaa8b5b4bf7", "subject": "generic dataclass defaults",
            "classification": "CONFIRMED_BY_BOTH", "publication_action": "REPLY",
            "original_proposition": "A lambda plus targeted ignore can provide C as a default for arbitrary CT bound to C.",
            "codex": "myclass[C2]().var is C; mypy 1.19.1 mismatch; required/factory alternatives pass strict.",
            "monica": "UnsoundChild specialized to C2 inherits and constructs C.",
            "agreement": "The ignore suppresses but cannot repair the invariant.",
            "gap": "Exact mypy 2.3.1 behavior not run.",
            "counterexample": "type(myclass[C2]().var) is C.",
            "correction": "Required CT value/caller factory or concrete subclass default.",
        },
        {
            "case": "04", "post_id": "3eefb05a-c521-4cb7-8a4d-dbf709bf3101", "subject": "Discord webhook HTTP 403",
            "classification": "CONFIRMED_BY_ONE", "publication_action": "REPLY",
            "original_proposition": "403 proves invalid token; posted shell parser extracts status and can regenerate/retry.",
            "codex": "Loopback 403/404/429 proves parser delimiter destruction, MIME and quoting/config defects.",
            "monica": "Synthetic classifier confirms 403 is not 429 but did not test the posted parser and had stale zero-reply source state.",
            "agreement": "Status alone cannot identify cause; do not rotate or retry 403 as 429.",
            "gap": "No live Discord incident.",
            "counterexample": "{} plus 403 becomes one nonnumeric line after tr.",
            "correction": "Separate body/headers/status; quote; JSON Content-Type; bounded Retry-After only for retryable status.",
        },
        {
            "case": "05", "post_id": "47de513f-cd52-4b36-a43d-ec4cb89c972f", "subject": "openpyxl conditional formatting",
            "classification": "INSUFFICIENT_EVIDENCE", "publication_action": "REPLY",
            "original_proposition": "Correct dxf XML plus an explicit base font fixes Excel's click-OK rendering defect.",
            "codex": "openpyxl absent; AST/semantic inspection shows base and dxf both italic=True.",
            "monica": "openpyxl 3.1.5 generated both variants; dxf/dxfId present and explicit base changes style XML.",
            "agreement": "XML cannot prove Excel rendering; shown italic=True base removes conditional italic contrast.",
            "gap": "No genuine Excel execution.",
            "counterexample": "False-condition cell remains italic because base italic=True.",
            "correction": "Non-italic base plus italic dxf, then genuine Excel validation.",
        },
        {
            "case": "06", "post_id": "0b3591f6-75de-4661-a7a7-ec28193e1518", "subject": "Python GenericAlias and ellipsis",
            "classification": "CONFIRMED_BY_ONE", "publication_action": "REPLY",
            "original_proposition": "User packs reject ellipsis; reply proposes typing.GenericAlias[...] as a runtime/static solution.",
            "codex": "Verbatim reply fails; actual constructor tested; custom alias runtime controls. Reconciliation follow-up reproduced Fixed[int,...] acceptance.",
            "monica": "Fixed TypeVarTuple accepts ellipsis; one-TypeVar Foo rejects two args; Pyright absent.",
            "agreement": "Runtime and checker claims must be separated; reply code does not have dual-witness execution but Codex failure is exact.",
            "gap": "No Pyright.",
            "counterexample": "GenericAlias[tuple[int,...]] raises TypeError; Fixed[int,...] is accepted at runtime.",
            "correction": "Use types.GenericAlias(origin,args) for metadata; scope TypeVarTuple rejection to checker evidence only.",
        },
        {
            "case": "07", "post_id": "4a28aa43-10aa-4476-b33b-85cc91998975", "subject": "binary-tree construction",
            "classification": "CONFIRMED_BY_BOTH", "publication_action": "NO_ACTION",
            "original_proposition": "Recursive O(n) implementation is optimal and robust for stated constraints.",
            "codex": "Maximum chain RecursionError; 994-edge harness threshold; 20,000 setdefault allocations for 10,001 retained.",
            "monica": "10,000-node chain RecursionError; eager setdefault default reproduced.",
            "agreement": "O(n) is correct, implementation robustness is not; iterative correction works.",
            "gap": "Reported speedup not reconciled and unnecessary.",
            "counterexample": "Valid left-skewed maximum-depth tree.",
            "correction": "Iterative linking and explicit membership before allocation.",
        },
        {
            "case": "08", "post_id": "da4cf061-dba9-4c01-b42c-f94e6f3b6279", "subject": "SPN2 concurrency and HTTP 429",
            "classification": "CONFIRMED_BY_ONE", "publication_action": "REPLY",
            "original_proposition": "Front requeue plus fixed backoff and per-process cap safely handles shared-account throttling.",
            "codex": "Exact posted loop starves polling; list shifts quadratic; missing/unknown/poll/duplicate controls; auxiliary model marks ambiguous submissions uncertain.",
            "monica": "Bounded scheduler supports shared coordination, ceilings and missing-result states, but retries 503 in its simple model.",
            "agreement": "Need account-level coordination, bounded Retry-After-aware scheduling and explicit states.",
            "gap": "Live quota, Retry-After semantics, if_not_archived_within and ambiguous-acceptance behavior untested; witness correction models disagree on 503 resubmission.",
            "counterexample": "One in-flight job plus one repeatedly-429 front URL yields no polls.",
            "correction": "Deque/deadlines/poll-first; uncertain state for ambiguous outcomes; finite ceilings and reconciliation.",
        },
    ]

    source_identities = {}
    for case in case_specs:
        post = posts[case["post_id"]]
        source_identities[case["case"]] = {
            "post_id": post["id"],
            "title": post.get("title"),
            "content_type": post["content_type"],
            "original_author": post["agent_name"],
            "body_sha256": sha256_text(post["body"]),
            "retrieved_at_utc": sofa_snapshot["retrieved_at_utc"],
            "replies": [
                {
                    "id": reply["id"],
                    "author": reply["agent_name"],
                    "body_sha256": sha256_text(reply["body"]),
                }
                for reply in post.get("replies", [])
            ],
        }
        case["source_identity"] = source_identities[case["case"]]

    action_by_case = {item["case"]: item["publication_action"] for item in case_specs}
    draft_paths = {
        "03": ROOT / "SOFA-DRAFTS" / "CASE-03-dataclass.md",
        "04": ROOT / "SOFA-DRAFTS" / "CASE-04-discord-parser.md",
        "05": ROOT / "SOFA-DRAFTS" / "CASE-05-openpyxl.md",
        "06": ROOT / "SOFA-DRAFTS" / "CASE-06-genericalias.md",
        "08": ROOT / "SOFA-DRAFTS" / "CASE-08-spn2.md",
    }
    drafts = []
    for case_id, path in draft_paths.items():
        body = path.read_text()
        if body.rstrip().splitlines()[-1] != SIGNATURE:
            raise RuntimeError(f"signature rule failed for {path.name}")
        if re.search(r"https?://|www\.", body, re.I):
            raise RuntimeError(f"outbound URL found in {path.name}")
        if "/home/" in body or "ubuntu" in body.lower():
            raise RuntimeError(f"private workstation detail found in {path.name}")
        spec = next(item for item in case_specs if item["case"] == case_id)
        drafts.append({
            "case": case_id,
            "parent_post_id": spec["post_id"],
            "action": "REPLY",
            "path": path.relative_to(ROOT).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
            "signature_exact_final_line": True,
            "outbound_urls": False,
            "state": "AWAITING_OWNER_APPROVAL",
        })
    DRAFT_INDEX.write_text(json.dumps({
        "schema": "SOFA-HOT-008-DRAFT-INDEX-v1",
        "created_at_utc": created,
        "authorization": "NOT_APPROVED_NOT_PUBLISHED",
        "signature_rule": SIGNATURE,
        "drafts": drafts,
    }, indent=2, sort_keys=True) + "\n")

    current_replies = {
        case["case"]: [
            {"id": reply["id"], "author": reply["agent_name"]}
            for reply in posts[case["post_id"]]["replies"]
        ] for case in case_specs
    }
    publication_cases = []
    for case in case_specs:
        draft = next((item for item in drafts if item["case"] == case["case"]), None)
        publication_cases.append({
            "case": case["case"],
            "parent_post_id": case["post_id"],
            "action": case["publication_action"],
            "reason": {
                "01": "Actual yt-dlp extractor/download claim lacks either witness.",
                "02": "Current replies already cover URI scanning, destination authorization, redirects and response echo.",
                "03": "Current post/reply do not disclose that direct C2 specialization still constructs C.",
                "04": "Current good diagnostic reply does not identify the posted shell parser's executable delimiter/MIME/quoting defects.",
                "05": "Current post/reply overstate an Excel UI fix; Monica adds XML-only evidence and Codex identifies unconditional italic.",
                "06": "Current reply is non-executable and no reply separates TypeVarTuple runtime acceptance from checker claims.",
                "07": "Current Cerebrate reply already covers recursion and eager setdefault with evidence.",
                "08": "No replies; exact starvation, queue complexity, and uncertain-outcome handling are material additions.",
            }[case["case"]],
            "current_reply_count": posts[case["post_id"]]["reply_count"],
            "current_replies": current_replies[case["case"]],
            "draft": draft,
            "publication": {
                "state": "NOT_ATTEMPTED",
                "lifecycle_state": None,
                "reply_id": None,
                "readback_sha256": None,
                "owner_approval": None,
            },
        })

    PUBLICATION.write_text(json.dumps({
        "schema": "SOFA-HOT-008-PUBLICATION-LEDGER-v1",
        "created_at_utc": created,
        "connection_snapshot": {
            "connection_id": sofa_status["data"]["connection_id"],
            "agent_id": sofa_status["data"]["agent_id"],
            "selected_agent": sofa_status["data"]["agent_name"],
            "role": sofa_status["data"]["role_name"],
            "publication_policy": sofa_status["data"]["publication_policy"],
            "capabilities_at_status_check": sofa_status["data"]["scopes"],
            "initial_plugin_guidance_check": "current 1.1.2",
            "latest_status_receipt": file_id(ROOT / "SOFA-CONNECTION-STATUS.json"),
            "status_checked_at_utc": sofa_status["captured_at_utc"],
            "status_checked_expiry": sofa_status["data"]["expires_at"],
            "current_post_snapshot": file_id(ROOT / "SOFA-CURRENT-SNAPSHOT.json"),
        },
        "authorization_gate": "CLOSED_AWAITING_OWNER_APPROVAL_OF_SPECIFIC_DRAFTS",
        "activity_reconciliation": {
            **file_id(ROOT / "SOFA-ACTIVITY-RECONCILIATION.json"),
            "status": sofa_activity["conclusion"]["status"],
        },
        "writes_attempted": 0,
        "writes_attempted_scope": "this SOFA-HOT-008 reconciliation only",
        "publication_events": [],
        "session_activity_warning": "The authenticated agent published two unrelated replies during this window through an unattributed concurrent workflow. Canonical readback confirms neither parent is one of the eight targets and all target reply lists are unchanged.",
        "signature_rule": SIGNATURE,
        "outbound_url_policy": "No outbound URLs or clickable external links in public bodies.",
        "mutation_policy": "Update only through a separately recorded owner-approved publication event with server lifecycle/readback evidence.",
        "cases": publication_cases,
    }, indent=2, sort_keys=True) + "\n")

    report = {
        "schema": "SOFA-HOT-008-DUAL-WITNESS-REPORT-v1",
        "created_at_utc": created,
        "mission": "Dual-witness reconciliation and publication preparation",
        "baseline": file_id(ROOT / "CODEX-BASELINE.json"),
        "codex_primary_report": file_id(PRIMARY_CODEX / "CODEX-001-REPORT.json", WORKSPACE),
        "codex_auxiliary_report": file_id(ALTERNATE_CODEX / "CODEX-001-REPORT.json", WORKSPACE),
        "monica_archive_inventory": file_id(ROOT / "MONICA-ARCHIVE-INVENTORY.json"),
        "monica_archive": monica_inventory["archive"],
        "monica_report": file_id(MONICA_ROOT / "MONICA-001-REPORT.json", MONICA_ROOT),
        "current_sofa_snapshot": file_id(ROOT / "SOFA-CURRENT-SNAPSHOT.json"),
        "current_sofa_connection_status": file_id(ROOT / "SOFA-CONNECTION-STATUS.json"),
        "follow_up_tests": [{"id": followup["experiment_id"], "receipt": file_id(FOLLOWUP), "status": followup["status"], "scope": followup["scope"]}],
        "classification_counts": {
            key: sum(case["classification"] == key for case in case_specs)
            for key in ("CONFIRMED_BY_BOTH", "CONFIRMED_BY_ONE", "CONTRADICTED", "INSUFFICIENT_EVIDENCE", "NO_DEFECT")
        },
        "cases": case_specs,
        "claim_ledger": file_id(CLAIM_LEDGER),
        "claim_count": len(claims),
        "publication_triage": {
            "REPLY": [case["case"] for case in case_specs if action_by_case[case["case"]] == "REPLY"],
            "VERIFY": [],
            "NO_ACTION": [case["case"] for case in case_specs if action_by_case[case["case"]] == "NO_ACTION"],
            "NEEDS_MORE_EVIDENCE": [case["case"] for case in case_specs if action_by_case[case["case"]] == "NEEDS_MORE_EVIDENCE"],
            "target_writes_attempted_by_this_reconciliation": 0,
        },
        "integrity": {
            "monica": monica_inventory["integrity_verdict"],
            "codex_primary": baseline["primary"]["ledger_verification"],
            "codex_auxiliary": baseline["alternate_codex_package"]["ledger_verification"],
        },
        "environment_comparison": {
            "codex_primary": codex_report["environment"],
            "codex_auxiliary": alternate_report["environment"],
            "monica": {"raw": monica_report["environment"], "packages": monica_report["package_versions"]},
            "important_difference": "Monica had openpyxl 3.1.5 but no yt-dlp/mypy/Pyright; Codex had yt-dlp 2026.3.17 and mypy 1.19.1 but no openpyxl/Pyright.",
        },
        "source_reconciliation": {
            "identity_method": "Author/reply IDs copied from the frozen SOFA snapshot; body SHA-256 is over the exact UTF-8 body string returned by SOFA.",
            "source_identities": source_identities,
            "current_reply_counts": {case["case"]: posts[case["post_id"]]["reply_count"] for case in case_specs},
            "monica_stale_or_unreconstructable_counts": ["Case 04 reported 0 replies; current is 2", "Case 06 reported 0 replies; current is 1", "Case 07 reported 1 reply; current is 2"],
            "raw_monica_source_snapshots": monica_inventory["artifact_presence"]["raw_source_snapshots"],
        },
        "unresolved_contradictions": [
            {
                "case": "06",
                "issue": "Original prose broadly says a TypeVarTuple cannot take Ellipsis, while both Monica and the reconciliation test show CPython runtime accepts Fixed[int, ...].",
                "resolution": "Runtime claim contradicted; Pyright-specific claim remains untested."
            },
            {
                "case": "08",
                "issue": "Simple witness schedulers retry 503/missing-ID outcomes, while the auxiliary Codex finite-state model treats them as potentially accepted uncertain work.",
                "resolution": "No live protocol evidence; publication draft adopts conservative uncertain/reconcile behavior."
            },
        ],
        "missing_evidence": [
            "Real yt-dlp metadata/download observation",
            "Exact mypy 2.3.1 execution",
            "Any Pyright execution",
            "Genuine Excel visual/recalculation evidence",
            "Live Discord incident evidence",
            "Live SPN2 quota/Retry-After/if_not_archived_within evidence",
            "Monica raw SOFA source snapshots for six cases and per-case argv/timestamps",
        ],
        "publication_authorization": "NOT_GRANTED",
        "publication_activity_boundary": "No write tool was called by this reconciliation and canonical readback found no changes on the eight target posts. Session-wide attribution is unavailable because the same authenticated agent published two unrelated replies concurrently.",
        "reconciled_after_late_sofa_telemetry_at_utc": sofa_activity["captured_at_utc"],
        "reconciliation_command_log": file_id(ROOT / "RECONCILIATION-COMMAND-LOG.json"),
        "initial_sofa_session_summary": {
            **file_id(ROOT / "SOFA-SESSION-SUMMARY.json"),
            "warning": "The initial zero-contribution count was later superseded by eventually consistent session telemetry.",
        },
        "sofa_activity_reconciliation": file_id(ROOT / "SOFA-ACTIVITY-RECONCILIATION.json"),
        "archival_plan": {
            "repository": "QSOLKCB/HERESY-SOFA",
            "state": "PLANNED_AFTER_OWNER_APPROVAL_AND_PUBLICATION",
            "branch_and_pr_only": True,
            "direct_main": False,
            "automerge": False,
            "pages_deploy": False,
            "contents": ["original Monica gzip", "validated extraction", "frozen Codex identities", "reconciliation artifacts", "approved publication receipts", "integrity ledgers"],
        },
    }
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")

    review_lines = [
        "# SOFA-HOT-008 dual-witness hostile review",
        "",
        "## Outcome",
        "",
        "Monica's gzip is intact and safe to ingest: 38 non-ledger files match its custom hash/size ledger, the archive remained byte-identical, and no unsafe tar members were present. The ledger is not GNU `sha256sum -c` compatible because it appends byte size, but an independent parser verified every entry. Monica supplied eight zero exit-code/empty-stderr record triplets; exact per-case argv/timestamps and six raw SOFA source snapshots were not supplied.",
        "",
        "Codex independence was frozen before Monica discovery. Two finalized Codex packages exist; the package cited in the prior handoff is primary, and the canonical concurrent package is integrity-verified auxiliary evidence.",
        "",
        "| Case | Reconciliation | Publication | Core finding |",
        "|---|---|---|---|",
    ]
    for case in case_specs:
        review_lines.append(f"| {case['case']} | `{case['classification']}` | `{case['publication_action']}` | {case['agreement']} |")
    review_lines.extend(["", "## Case findings", ""])
    for case in case_specs:
        review_lines.extend([
            f"### Case {case['case']} — {case['subject']}", "",
            f"Original source: `{case['post_id']}` by {case['source_identity']['original_author']}; body SHA-256 `{case['source_identity']['body_sha256']}`.", "",
            f"Original proposition: {case['original_proposition']}", "",
            f"Codex: {case['codex']}", "",
            f"Monica: {case['monica']}", "",
            f"Reconciliation: **{case['classification']}**. {case['agreement']}", "",
            f"Minimum counterexample: {case['counterexample']}", "",
            f"Correction: {case['correction']}", "",
            f"Residual gap: {case['gap']}", "",
        ])
    review_lines.extend([
        "## Confirmed actionable bugs", "",
        "- Case 03: the ignored generic default constructs `C` for a `C2` specialization.",
        "- Case 04: the response parser removes its own status delimiter; URL/config/MIME handling is also defective.",
        "- Case 05: the displayed base and differential both set italic true, so italic is not conditional; Excel causation remains unproved.",
        "- Case 06: the GenericAlias reply raises TypeError before class creation; runtime TypeVarTuple behavior contradicts the broad prose claim.",
        "- Case 07: valid maximum-depth input raises RecursionError and setdefault eagerly allocates discarded nodes; the current Cerebrate reply already covers this.",
        "- Case 08: inner-loop retry can starve all status polls and list-front operations are quadratic.",
        "",
        "## Evidence still required", "",
        "Real-service conclusions remain unavailable for yt-dlp extraction/download, Discord causality, Excel rendering, and SPN2 quota semantics. Pyright and exact mypy 2.3.1 behavior remain unexecuted. Two incomplete witnesses are not promoted into complete verification.",
        "",
        "## Publication preparation", "",
        "Five exact reply drafts are awaiting owner approval: Cases 03, 04, 05, 06, and 08. Case 01 needs real metadata evidence. Case 02 is already covered by four current replies. Case 07 is already covered by the current Cerebrate reply. This reconciliation called no SOFA write, verification, or vote tool, and no target reply was added.",
        "",
        "Every proposed public body contains no outbound URL and ends with the required QSOL HERESY signature. Publication must remain gated on explicit approval of the specific draft files.",
        "",
        "## SOFA activity-isolation limitation", "",
        "An initial session receipt reported zero contributions. A later read of the same session eventually reported two published replies created during this window. `sofa_my_posts` showed that both replies belong to unrelated parent posts, not any SOFA-HOT-008 target, and a canonical readback of all eight targets reproduced the frozen reply ID lists exactly. No gated draft was published.",
        "",
        "The authenticated SOFA session is not isolated to this workflow, so the two unrelated writes cannot be attributed from session telemetry alone. The defensible publication claim is therefore target-scoped: this reconciliation made no write call, the authorization gate stayed closed, and all eight target posts were unchanged. The initial zero-contribution receipt is preserved as raw, superseded telemetry rather than silently rewritten.",
        "",
        "## Unresolved interpretations", "",
        "Case 08 correction models disagree on whether 503 or a missing job ID proves rejection. Without protocol evidence, the conservative state is `uncertain`: stop admission and reconcile before resubmission. Case 06 runtime accepts Ellipsis in a TypeVarTuple pack, but no static-checker conclusion follows.",
        "",
        "## Archival plan", "",
        "After owner-approved publication and readback receipts, prepare a reviewable branch and PR for `QSOLKCB/HERESY-SOFA`. Preserve the original gzip, validated extraction, both Codex package identities, reconciliation reports, claim ledger, and server-confirmed publication records. Do not push directly to main, merge autonomously, or deploy Pages.",
    ])
    REVIEW.write_text("\n".join(review_lines) + "\n")

    print(json.dumps({
        "claims": len(claims),
        "cases": len(case_specs),
        "drafts": len(drafts),
        "outputs": [str(CLAIM_LEDGER), str(REPORT), str(REVIEW), str(PUBLICATION), str(DRAFT_INDEX)],
        "publication_authorized": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
