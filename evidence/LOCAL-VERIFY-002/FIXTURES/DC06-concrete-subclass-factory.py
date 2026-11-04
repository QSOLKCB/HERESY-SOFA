"""A concrete subclass safely owns both its annotation and factory."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Generic, TYPE_CHECKING, TypeVar


@dataclass
class C:
    pass


@dataclass
class C2(C):
    pass


CT = TypeVar("CT", bound=C)


@dataclass
class GenericBase(Generic[CT]):
    var: CT


@dataclass
class ConcreteChild(GenericBase[C2]):
    var: C2 = field(default_factory=C2)


value: ConcreteChild = ConcreteChild()
if TYPE_CHECKING:
    reveal_type(value.var)

print(json.dumps({"runtime_var_type": type(value.var).__name__}, sort_keys=True))
