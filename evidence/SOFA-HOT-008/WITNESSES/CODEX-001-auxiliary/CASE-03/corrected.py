from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

@dataclass
class C:
    pass

@dataclass
class C2(C):
    value: int = 2

CT = TypeVar('CT', bound=C)

@dataclass
class Box(Generic[CT]):
    var: CT

def from_factory(factory: Callable[[], CT]) -> Box[CT]:
    return Box(factory())

explicit: Box[C2] = Box(C2())
manufactured: Box[C2] = from_factory(C2)
assert isinstance(explicit.var, C2) and isinstance(manufactured.var, C2)
