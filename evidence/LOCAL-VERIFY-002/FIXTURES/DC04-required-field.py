"""Sound generic base: the value is required from the caller."""

from __future__ import annotations

from dataclasses import dataclass
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
class RequiredField(Generic[CT]):
    var: CT


value: RequiredField[C2] = RequiredField(C2())
if TYPE_CHECKING:
    reveal_type(value.var)

print(json.dumps({"runtime_var_type": type(value.var).__name__}, sort_keys=True))
