#!/usr/bin/env python3
"""Native runtime controls for LOCAL-VERIFY-001 investigations A and B."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import platform
import random
import sys
from types import GenericAlias
from typing import Any, Callable, Generic, TypeVar, TypeVarTuple, get_args, get_origin


SEED = 26051105
T = TypeVar("T")
Ts = TypeVarTuple("Ts")


class Single(Generic[T]):
    pass


class Packed(Generic[*Ts]):
    pass


class RuntimeOnly:
    seen: object | None = None

    @classmethod
    def __class_getitem__(cls, params: object) -> tuple[type[RuntimeOnly], object]:
        cls.seen = params
        return (cls, params)


@dataclass
class C:
    pass


@dataclass
class C2(C):
    pass


CT = TypeVar("CT", bound=C)


@dataclass
class myclass(Generic[CT]):
    var: CT = field(default_factory=lambda: C())  # type: ignore[assignment]


@dataclass
class myclass_child(myclass[C2]):
    var: C2 = field(default_factory=C2)


@dataclass
class RequiredField(Generic[CT]):
    var: CT


@dataclass
class CallerFactory(Generic[CT]):
    factory: Callable[[], CT]
    var: CT = field(init=False)

    def __post_init__(self) -> None:
        self.var = self.factory()


@dataclass
class ConcreteBase(Generic[CT]):
    var: CT


@dataclass
class ConcreteChild(ConcreteBase[C2]):
    var: C2 = field(default_factory=C2)


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
        evidence_class: str = "EXECUTED_NATIVE",
        negative_control: bool = False,
    ) -> None:
        self.assertions.append({
            "test_id": test_id,
            "passed": bool(condition),
            "expected": expected,
            "actual": actual,
            "evidence_class": evidence_class,
            "negative_control": negative_control,
        })
        if not condition:
            raise AssertionError(f"{test_id}: expected {expected!r}, observed {actual!r}")


def alias_summary(value: object) -> dict[str, Any]:
    return {
        "repr": repr(value),
        "origin_repr": repr(get_origin(value)),
        "args_repr": [repr(arg) for arg in get_args(value)],
        "runtime_type": f"{type(value).__module__}.{type(value).__qualname__}",
    }


def main() -> int:
    random.seed(SEED)
    record = Recorder()
    observations: dict[str, Any] = {}

    # A2: the actual constructor accepts an origin and an args object.
    alias = GenericAlias(tuple, (int, Ellipsis))
    summary = alias_summary(alias)
    observations["types_generic_alias"] = summary
    record.check("A2-origin", get_origin(alias) is tuple, expected="tuple", actual=summary["origin_repr"])
    record.check(
        "A2-args", get_args(alias) == (int, Ellipsis),
        expected=["<class 'int'>", "Ellipsis"], actual=summary["args_repr"],
    )
    record.check(
        "A2-repr", repr(alias) == "tuple[int, ...]",
        expected="tuple[int, ...]", actual=repr(alias),
    )
    unchecked = alias((1, "not-an-int"))
    observations["generic_alias_unchecked_value"] = list(unchecked)
    record.check(
        "A2-no-runtime-enforcement", unchecked == (1, "not-an-int"),
        expected=[1, "not-an-int"], actual=list(unchecked), negative_control=True,
    )

    # A3: CPython runtime subscription accepts each element as metadata.
    runtime_forms = {
        "single": Packed[int],
        "heterogeneous": Packed[int, str],
        "repeated": Packed[int, int, int],
        "literal_ellipsis": Packed[int, ...],
        "ellipsis_only": Packed[...],
    }
    observations["typevartuple_runtime_forms"] = {
        name: alias_summary(value) for name, value in runtime_forms.items()
    }
    record.check(
        "A3-single", get_args(runtime_forms["single"]) == (int,),
        expected=["int"], actual=[getattr(x, "__name__", repr(x)) for x in get_args(runtime_forms["single"])],
    )
    record.check(
        "A3-heterogeneous", get_args(runtime_forms["heterogeneous"]) == (int, str),
        expected=["int", "str"], actual=[getattr(x, "__name__", repr(x)) for x in get_args(runtime_forms["heterogeneous"])],
    )
    record.check(
        "A3-repeated", get_args(runtime_forms["repeated"]) == (int, int, int),
        expected=["int", "int", "int"], actual=[getattr(x, "__name__", repr(x)) for x in get_args(runtime_forms["repeated"])],
    )
    record.check(
        "A3-literal-ellipsis", get_args(runtime_forms["literal_ellipsis"]) == (int, Ellipsis),
        expected=["int", "Ellipsis"], actual=[getattr(x, "__name__", repr(x)) for x in get_args(runtime_forms["literal_ellipsis"])],
        negative_control=True,
    )
    record.check(
        "A3-ellipsis-only", get_args(runtime_forms["ellipsis_only"]) == (Ellipsis,),
        expected=["Ellipsis"], actual=[repr(x) for x in get_args(runtime_forms["ellipsis_only"])],
        negative_control=True,
    )

    try:
        Single[int, str]
    except Exception as exc:  # noqa: BLE001 - exact native exception is evidence
        observations["single_too_many_args"] = {
            "exception_type": type(exc).__name__, "message": str(exc),
        }
        record.check(
            "A5-single-too-many", isinstance(exc, TypeError),
            expected="TypeError", actual=type(exc).__name__, negative_control=True,
        )
    else:
        record.check(
            "A5-single-too-many", False,
            expected="TypeError", actual="accepted", negative_control=True,
        )

    hook_result = RuntimeOnly[int, ...]
    observations["custom_class_getitem"] = {
        "returned_class": hook_result[0].__name__,
        "params_repr": repr(hook_result[1]),
        "typing_origin": repr(get_origin(hook_result)),
        "typing_args": [repr(arg) for arg in get_args(hook_result)],
    }
    record.check(
        "A5-class-getitem-runs", hook_result[1] == (int, Ellipsis),
        expected="(int, Ellipsis)", actual=repr(hook_result[1]), negative_control=True,
    )
    record.check(
        "A5-class-getitem-not-typing-alias", get_origin(hook_result) is None,
        expected="no typing origin", actual=repr(get_origin(hook_result)), negative_control=True,
    )

    # B: parameterization is erased when the inherited factory executes.
    base_c = myclass[C]()
    base_c2 = myclass[C2]()
    child = myclass_child()
    observations["posted_dataclass_defaults"] = {
        "myclass[C]": type(base_c.var).__name__,
        "myclass[C2]": type(base_c2.var).__name__,
        "myclass_child": type(child.var).__name__,
    }
    record.check("B-default-C", type(base_c.var) is C, expected="C", actual=type(base_c.var).__name__)
    record.check(
        "B-default-C2-violates-parameter", not isinstance(base_c2.var, C2),
        expected="not C2", actual=type(base_c2.var).__name__, negative_control=True,
    )
    record.check("B-child-override", type(child.var) is C2, expected="C2", actual=type(child.var).__name__)

    required = RequiredField[C2](C2())
    factory = CallerFactory[C2](C2)
    concrete = ConcreteChild()
    observations["sound_dataclass_designs"] = {
        "required_field": type(required.var).__name__,
        "caller_factory": type(factory.var).__name__,
        "concrete_override": type(concrete.var).__name__,
    }
    record.check("B-required-field", type(required.var) is C2, expected="C2", actual=type(required.var).__name__)
    record.check("B-caller-factory", type(factory.var) is C2, expected="C2", actual=type(factory.var).__name__)
    record.check("B-concrete-override", type(concrete.var) is C2, expected="C2", actual=type(concrete.var).__name__)

    output = {
        "schema_version": "1.0",
        "campaign": "LOCAL-VERIFY-001",
        "seed": SEED,
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "assertion_count": len(record.assertions),
        "failed_assertion_count": sum(not item["passed"] for item in record.assertions),
        "negative_control_count": sum(item["negative_control"] for item in record.assertions),
        "assertions": record.assertions,
        "observations": observations,
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
