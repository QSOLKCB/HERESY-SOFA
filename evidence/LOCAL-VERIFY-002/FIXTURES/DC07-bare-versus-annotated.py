"""Bare construction versus explicit generic annotations."""

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


bare = MyClass()
annotated_c: MyClass[C] = MyClass()
annotated_c2: MyClass[C2] = MyClass()

if TYPE_CHECKING:
    reveal_type(bare)
    reveal_type(annotated_c.var)
    reveal_type(annotated_c2.var)

print(json.dumps({
    "annotated_C": type(annotated_c.var).__name__,
    "annotated_C2": type(annotated_c2.var).__name__,
    "bare": type(bare.var).__name__,
}, sort_keys=True))
