"""The narrow ignore silences mypy but cannot make the runtime default sound."""

from dataclasses import dataclass, field
from typing import Generic, TypeVar


@dataclass
class C:
    pass


@dataclass
class C2(C):
    pass


CT = TypeVar("CT", bound=C)


@dataclass
class MyClass(Generic[CT]):
    var: CT = field(default_factory=lambda: C())  # type: ignore[assignment]


claims_c2: MyClass[C2] = MyClass()
