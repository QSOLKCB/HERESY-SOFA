#!/usr/bin/env python3
import argparse
import importlib.metadata
import json
import shutil
import subprocess
import sys
import typing
from datetime import datetime, timezone
from pathlib import Path
from types import GenericAlias
from typing import get_args, get_origin

import corrected_runtime
from original_custom_alias import Foo

SEED = 26051108


def run(command, cwd):
    completed = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)
    return {"command": command, "exit_code": completed.returncode,
            "stdout": completed.stdout, "stderr": completed.stderr}


def main(receipt_path):
    started = datetime.now(timezone.utc).isoformat()
    root = Path(__file__).resolve().parent
    checks = []

    def check(name, actual, expected, classification="EXECUTED"):
        checks.append({"name": name, "actual": actual, "expected": expected,
                       "passed": actual == expected, "classification": classification})

    alias = Foo[int, ...]
    instance = alias(1, 2, 3)
    check("custom_alias_runtime_constructs", instance._values, (1, 2, 3))
    check("custom_alias_repr", repr(alias), "Foo[int, ...]")
    bad_type = False
    try:
        alias(1, "x")
    except TypeError:
        bad_type = True
    check("custom_alias_runtime_type_check", bad_type, True)
    bad_arity = False
    try:
        Foo[int, str](1)
    except TypeError:
        bad_arity = True
    check("custom_alias_runtime_arity_check", bad_arity, True)

    verbatim = run([sys.executable, "reply_verbatim.py"], root)
    check("reply_verbatim_fails", verbatim["exit_code"] != 0, True)
    check("typing_GenericAlias_import_succeeds_on_this_python",
          typing.GenericAlias is GenericAlias, True)
    check("reply_fails_at_GenericAlias_subscript",
          "not subscriptable" in verbatim["stderr"], True)

    follow_on = run([
        sys.executable, "-c",
        "from types import GenericAlias; "
        "T=GenericAlias[tuple[int, ...]]; "
        "print(repr(T)); "
        "exec('class Foo(GenericAlias[tuple[int, ...]]):\\n    pass')"
    ], root)
    check("correct_import_follow_on_class_declaration_fails", follow_on["exit_code"] != 0, True)

    actual_base = run([
        sys.executable, "-c",
        "from types import GenericAlias; from typing import get_origin,get_args; "
        "A=GenericAlias(tuple,(int,...)); "
        "exec('class Foo(A):\\n    pass',globals()); "
        "print(get_origin(Foo)); print(get_args(Foo)); print(Foo.__mro__[1].__name__)"
    ], root)
    check("actual_alias_base_discards_alias_metadata_on_class",
          actual_base["stdout"].splitlines(), ["None", "()", "tuple"])

    tuple_alias = GenericAlias(tuple, (int, ...))
    check("actual_constructor_origin", get_origin(tuple_alias).__name__, "tuple")
    check("actual_constructor_args", [getattr(x, "__name__", repr(x)) for x in get_args(tuple_alias)],
          ["int", "Ellipsis"])
    check("actual_constructor_equals_builtin", tuple_alias == tuple[int, ...], True)
    runtime_instance = corrected_runtime.runtime_alias(1, "not-an-int")
    check("GenericAlias_does_not_enforce_runtime_arguments",
          runtime_instance.values, (1, "not-an-int"))

    one_arg_error = False
    try:
        GenericAlias(tuple)
    except TypeError:
        one_arg_error = True
    check("actual_constructor_requires_origin_and_args", one_arg_error, True)

    pyright_path = shutil.which("pyright")
    if pyright_path:
        pyright_version = run([pyright_path, "--version"], root)
        pyright_run = run([pyright_path, "original_custom_alias.py"], root)
        pyright = {"classification": "EXECUTED", "version": pyright_version,
                   "run": pyright_run}
    else:
        try:
            version = importlib.metadata.version("pyright")
        except importlib.metadata.PackageNotFoundError:
            version = None
        pyright = {"classification": "NOT_TESTED", "version": version,
                   "reason": "Pyright executable is not installed."}

    passed = all(item["passed"] for item in checks)
    receipt = {
        "case": "CASE-06",
        "source_id": "0b3591f6-75de-4661-a7a7-ec28193e1518",
        "source_author": "midhun-hermes",
        "reply_id": "a66cf887-724d-41f9-843f-d0d9548b0b84",
        "reply_author": "Milo Humanizer",
        "seed": SEED,
        "started_utc": started,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "command": "uv run --no-project --offline --no-managed-python python test_case_06.py --receipt receipt.json",
        "process_exit_code": 0 if passed else 1,
        "verbatim_run": verbatim,
        "correct_import_follow_on": follow_on,
        "actual_constructor_base_run": actual_base,
        "pyright": pyright,
        "checks": checks,
        "conclusion": {
            "classification": "CONFIRMED_DEFECT",
            "executed": "The post's custom alias works at runtime for its stated checks.",
            "defect": "On CPython 3.14 typing.GenericAlias imports as the types.GenericAlias compatibility name, but that class is not subscriptable, so the reply fails on its first alias expression and never reaches the class declaration. The real constructor takes (origin, args), alias-as-base produces a tuple subclass without get_origin/get_args metadata on the class, and no runtime value validation occurs.",
            "not_tested": "Pyright claims, because Pyright is absent.",
            "minimal_correction": "Use separate statically typed Fixed/Variadic forms; for runtime metadata only use types.GenericAlias(origin, args), or retain a custom alias with an explicit static-checking limitation."
        }
    }
    Path(receipt_path).write_text(json.dumps(receipt, indent=2, sort_keys=True, default=list) + "\n")
    print(json.dumps({"case": "CASE-06", "passed": passed,
                      "pyright": pyright["classification"]}, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", required=True)
    raise SystemExit(main(parser.parse_args().receipt))
