"""Negative control: the checker must reject an intentionally wrong exact type."""

from dataclasses import dataclass
from typing import assert_type, Generic, TypeVar


@dataclass
class C:
    pass


@dataclass
class C2(C):
    pass


CT = TypeVar("CT", bound=C)


@dataclass
class RequiredField(Generic[CT]):
    var: CT


value: RequiredField[C2] = RequiredField(C2())
assert_type(value.var, C)
print(type(value.var).__name__)
