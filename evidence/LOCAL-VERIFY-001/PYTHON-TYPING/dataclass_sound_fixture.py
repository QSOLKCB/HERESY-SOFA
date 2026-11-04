"""Three sound designs: required field, caller factory, concrete override."""

from dataclasses import dataclass, field
from typing import Callable, Generic, TypeVar


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


required: RequiredField[C2] = RequiredField(C2())
factory: CallerFactory[C2] = CallerFactory(C2)
child: ConcreteChild = ConcreteChild()
