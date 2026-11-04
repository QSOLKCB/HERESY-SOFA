"""Static-checker negative and positive controls for GenericAlias/TypeVarTuple."""

from typing import Any, Generic, TypeVar, TypeVarTuple
from types import GenericAlias


T = TypeVar("T")
Ts = TypeVarTuple("Ts")


class Single(Generic[T]):
    pass


class Packed(Generic[*Ts]):
    pass


class RuntimeOnly:
    @classmethod
    def __class_getitem__(cls, params: object) -> object:
        return (cls, params)


valid_single: type[Single[int]] = Single[int]
valid_pack: type[Packed[int, str, int]] = Packed[int, str, int]

# Negative controls: CPython accepts the pack ellipsis and runtime hook, but a
# static checker need not recognize either as a useful type form.
pack_with_ellipsis: type[Packed[int, ...]] = Packed[int, ...]
too_many_single: type[Single[int, str]] = Single[int, str]
runtime_hook_value: Any = RuntimeOnly[int, ...]

# Runtime metadata is intentionally dynamic and carries no element enforcement.
runtime_alias = GenericAlias(tuple, (int, Ellipsis))
runtime_value: tuple[int, ...] = runtime_alias((1, "not-an-int"))
