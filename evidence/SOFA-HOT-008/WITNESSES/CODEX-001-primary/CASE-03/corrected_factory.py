"""Sound convenience design: pass an explicit factory to a typed constructor function."""

from dataclasses import dataclass
from typing import Callable, Generic, TypeVar


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


def make_myclass(factory: Callable[[], CT]) -> MyClass[CT]:
    return MyClass(factory())


claims_c2: MyClass[C2] = make_myclass(C2)
