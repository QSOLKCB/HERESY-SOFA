"""The posted ignored factory: checker metadata and runtime value disagree."""

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


declared: MyClass[C2] = MyClass[C2]()
reveal_type(declared.var)
