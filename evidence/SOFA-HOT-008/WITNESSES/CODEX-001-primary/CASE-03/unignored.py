from dataclasses import dataclass, field
from typing import Generic, TypeVar


@dataclass
class C:
    pass


CT = TypeVar("CT", bound=C)


@dataclass
class MyClass(Generic[CT]):
    var: CT = field(default_factory=lambda: C())
