"""Sound construction with a caller-supplied typed factory."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Callable, Generic, TYPE_CHECKING, TypeVar


@dataclass
class C:
    pass


@dataclass
class C2(C):
    pass


CT = TypeVar("CT", bound=C)


@dataclass
class CallerFactory(Generic[CT]):
    factory: Callable[[], CT]
    var: CT = field(init=False)

    def __post_init__(self) -> None:
        self.var = self.factory()


value: CallerFactory[C2] = CallerFactory(C2)
if TYPE_CHECKING:
    reveal_type(value.var)

print(json.dumps({"runtime_var_type": type(value.var).__name__}, sort_keys=True))
