#!/usr/bin/env python3
import argparse
import ast
import importlib.metadata
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

from corrected_intent import effective_italic

SEED = 26051108


def main(receipt_path):
    started = datetime.now(timezone.utc).isoformat()
    root = Path(__file__).resolve().parent
    checks = []

    def check(name, actual, expected, classification="EXECUTED"):
        checks.append({"name": name, "actual": actual, "expected": expected,
                       "passed": actual == expected, "classification": classification})

    spec = importlib.util.find_spec("openpyxl")
    if spec is None:
        openpyxl_version = None
        dependency_status = "NOT_TESTED"
    else:
        openpyxl_version = importlib.metadata.version("openpyxl")
        dependency_status = "EXECUTED"

    tree = ast.parse((root / "original_fix.py").read_text())
    italic_true_calls = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            for keyword in node.keywords:
                if keyword.arg == "italic" and isinstance(keyword.value, ast.Constant) \
                        and keyword.value.value is True:
                    italic_true_calls += 1
    check("proposed_fix_sets_italic_true_twice", italic_true_calls, 2)

    original_false = effective_italic(True, True, False)
    original_true = effective_italic(True, True, True)
    check("proposed_fix_false_condition_is_already_italic", original_false, True, "INFERRED")
    check("proposed_fix_has_no_italic_state_contrast", original_false == original_true, True,
          "INFERRED")
    corrected_false = effective_italic(False, True, False)
    corrected_true = effective_italic(False, True, True)
    check("corrected_intent_false_condition_not_italic", corrected_false, False, "INFERRED")
    check("corrected_intent_true_condition_italic", corrected_true, True, "INFERRED")

    xlsx_checks = {
        "classification": "NOT_TESTED" if spec is None else "NOT_EXECUTED",
        "items": ["ZIP package relationships", "styles.xml dxfs", "sheet dxfId",
                  "formula", "priority", "base cell style"],
        "reason": "openpyxl is not installed" if spec is None else "not reached"
    }
    excel_rendering = {
        "classification": "NOT_TESTED",
        "reason": "No genuine Microsoft Excel rendering/recalculation evidence was available; LibreOffice was not used."
    }

    passed = all(item["passed"] for item in checks)
    receipt = {
        "case": "CASE-05",
        "source_id": "47de513f-cd52-4b36-a43d-ec4cb89c972f",
        "source_author": "midhun-hermes",
        "reply_id": "cc4b752b-74c3-478f-8c53-6abd3ca4e837",
        "reply_author": "Milo Humanizer",
        "seed": SEED,
        "started_utc": started,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "command": "uv run --no-project --offline --no-managed-python python test_case_05.py --receipt receipt.json",
        "process_exit_code": 0 if passed else 1,
        "openpyxl": {"classification": dependency_status, "version": openpyxl_version},
        "xlsx_xml": xlsx_checks,
        "excel_rendering": excel_rendering,
        "checks": checks,
        "conclusion": {
            "classification": "INCOMPLETE",
            "executed": "AST inspection confirms the proposed base and differential both set italic=True.",
            "inferred_defect": "A false-condition cell is unconditionally italic under the shown fix, so italic cannot be the visible conditional delta.",
            "not_tested": "openpyxl serialization and genuine Excel rendering claims.",
            "minimal_correction": "If conditional italic is intended, use an explicit non-italic base and italic dxf, then verify styles.xml/dxfId/formula and test in genuine Excel before claiming a UI fix."
        }
    }
    Path(receipt_path).write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"case": "CASE-05", "passed": passed,
                      "openpyxl": dependency_status, "excel": "NOT_TESTED"}, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", required=True)
    raise SystemExit(main(parser.parse_args().receipt))
