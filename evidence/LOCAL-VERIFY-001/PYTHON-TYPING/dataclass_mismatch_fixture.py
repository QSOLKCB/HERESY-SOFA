"""The bound-TypeVar/default-factory mismatch without suppression."""

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
    var: CT = field(default_factory=lambda: C())


declared: MyClass[C2] = MyClass[C2]()
