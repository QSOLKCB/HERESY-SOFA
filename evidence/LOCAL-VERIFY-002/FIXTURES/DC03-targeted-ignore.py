"""A targeted ignore silences the checker but cannot change the factory."""

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
class MyClass(Generic[CT]):
    var: CT = field(default_factory=lambda: C())  # type: ignore[assignment]


value: MyClass[C2] = MyClass[C2]()
if TYPE_CHECKING:
    reveal_type(value.var)

print(json.dumps({
    "declared": "MyClass[C2]",
    "runtime_var_type": type(value.var).__name__,
    "satisfies_C2": isinstance(value.var, C2),
}, sort_keys=True))
