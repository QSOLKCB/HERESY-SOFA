"""Sound design: require the generic value."""

from dataclasses import dataclass
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
    var: CT


claims_c2: MyClass[C2] = MyClass(C2())
