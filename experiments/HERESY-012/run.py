"""HERESY-012: independent bounded reproduction of JUnit parameter-name laundering.

Models the *original* QEC #623 count-and-family verifier and a corrected
exact-node-ID verifier. Inputs are synthetic standard-library XML fixtures,
NOT imported QEC execution artifacts, and nothing is published to SOFA.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json
import sys
import xml.etree.ElementTree as ET

CASE = "test_phase623_wire_each_revocation_denies_before_any_output"
DIMENSIONS = (
    "operation-REVOKED_OPERATION",
    "signer-REVOKED_SIGNER",
    "capability-REVOKED_CAPABILITY",
    "policy-REVOKED_POLICY",
)
SINGLES = (
    "test_phase623_wire_allow_once_replay_denied_and_receipts",
    "test_phase623_wire_transplant_individually_valid_bundle_is_denied",
    "test_phase623_wire_reused_operation_identity_denied_after_rotation",
    "test_phase623_wire_wrong_client_and_channel_have_zero_protected_effect",
    "test_phase623_wire_tampered_proof_and_policy_fail_closed_then_valid",
    "test_phase623_wire_saturated_ledger_blocks_otherwise_valid_action",
    "test_phase623_ledger_chain_independently_rejects_tampering",
)
FAMILY_COUNTS = {**{name: 1 for name in SINGLES}, CASE: 4}
EXACT_NODES = frozenset((*SINGLES, *(CASE + "[" + name + "]" for name in DIMENSIONS)))
MODULE = "test_phase623_end_to_end"


def make_xml(*, parameters=DIMENSIONS, status=None, omit=(), module=MODULE):
    """Synthetic JUnit; no real test suite is executed by this fixture."""
    suite = ET.Element("testsuite")
    for name in (*SINGLES, *(CASE + "[" + item + "]" for item in parameters)):
        if name in omit:
            continue
        element = ET.SubElement(suite, "testcase", {"classname": module, "name": name})
        if status and name == SINGLES[0]:
            ET.SubElement(element, status, {"message": "synthetic negative control"})
    return ET.tostring(suite, encoding="utf-8")


def original_accepts(xml):
    """Intentionally flawed historical *logic pattern*, not a QEC import."""
    try:
        root = ET.fromstring(xml)
        cases = list(root.iter("testcase"))
        if len(cases) != 11:
            return False
        counts = Counter()
        seen = set()
        for case in cases:
            name = case.attrib.get("name", "")
            family = name.split("[", 1)[0]
            if family not in FAMILY_COUNTS or name in seen:
                return False
            if MODULE not in case.attrib.get("classname", ""):
                return False
            if any(case.find(tag) is not None for tag in ("failure", "error", "skipped")):
                return False
            seen.add(name)
            counts[family] += 1
        return dict(counts) == FAMILY_COUNTS
    except (ET.ParseError, TypeError):
        return False


def corrected_accepts(xml):
    """Only a complete, exactly named, passing eleven-node inventory passes."""
    try:
        root = ET.fromstring(xml)
        cases = list(root.iter("testcase"))
        if len(cases) != len(EXACT_NODES):
            return False
        names = set()
        for case in cases:
            name = case.attrib.get("name", "")
            if name not in EXACT_NODES or name in names:
                return False
            if case.attrib.get("classname") != MODULE:
                return False
            if any(case.find(tag) is not None for tag in ("failure", "error", "skipped")):
                return False
            names.add(name)
        return names == EXACT_NODES
    except (ET.ParseError, TypeError):
        return False


def run():
    legitimate = make_xml()
    # Codex P2 counterexample: four distinct *operation-only* nodes, with
    # neither signer nor capability nor policy revocation observed.
    operation_only = make_xml(parameters=tuple(
        "operation-REVOKED_OPERATION-" + str(i) for i in range(4)
    ))
    wrong_reason = make_xml(parameters=(
        "operation-REVOKED_SIGNER", *DIMENSIONS[1:],
    ))
    absent = make_xml(omit=(SINGLES[0],))
    unrelated = make_xml(module="unrelated_unit_test")
    controls = {
        "valid_eleven_old_accepts": original_accepts(legitimate),
        "valid_eleven_corrected_accepts": corrected_accepts(legitimate),
        "operation_only_has_eleven_distinct_nodes": (
            len({case.attrib["name"] for case in ET.fromstring(operation_only)}) == 11
        ),
        "operation_only_old_incorrectly_accepts": original_accepts(operation_only),
        "operation_only_corrected_rejects": not corrected_accepts(operation_only),
        "wrong_reason_old_incorrectly_accepts": original_accepts(wrong_reason),
        "wrong_reason_corrected_rejects": not corrected_accepts(wrong_reason),
        "missing_node_both_reject": not original_accepts(absent) and not corrected_accepts(absent),
        "unrelated_module_both_reject": not original_accepts(unrelated) and not corrected_accepts(unrelated),
        "failed_case_both_reject": all(
            not original_accepts(make_xml(status=tag))
            and not corrected_accepts(make_xml(status=tag))
            for tag in ("failure", "error", "skipped")
        ),
        "altered_case_identity_is_not_an_execution": True,
    }
    successful = all(controls.values())
    output = {
        "claims": {
            "family_counts_can_launder_missing_parameter_dimensions":
                "executed" if successful else "not_tested",
            "exact_parameter_identity_check_rejects_substitution":
                "executed" if successful else "not_tested",
            "original_qec_run_omitted_revocations": "unsupported",
            "real_qec_security_tests_executed_here": "not_tested",
        },
        "observations": {
            "all_checks_passed": successful,
            "checks": controls,
            "synthetic_junit_test_count": 11,
            "expected_revocation_parameters": list(DIMENSIONS),
            "substituted_revocation_parameters": [
                "operation-REVOKED_OPERATION-" + str(i) for i in range(4)
            ],
            "legitimate_xml_sha256": hashlib.sha256(legitimate).hexdigest(),
            "substituted_xml_sha256": hashlib.sha256(operation_only).hexdigest(),
            "fixture": "Python standard-library generated synthetic JUnit XML; no QEC code or live test suite",
            "source_scope": "Independent conceptual reproduction of QEC #623's original family-count logic",
        },
        "mitigation": (
            "Require the exact independently specified set of test node IDs "
            "including every parametrized dimension and rejection reason, "
            "reject missing/failed/skipped entries, and retain CI JUnit evidence."
        ),
    }
    print(json.dumps(output, sort_keys=True, ensure_ascii=True, allow_nan=False))
    return 0 if successful else 1


if __name__ == "__main__":
    sys.exit(run())
