"""Runtime interception works even when static generic syntax is rejected."""

from __future__ import annotations

import json
from typing import Any, Generic, TYPE_CHECKING, TypeVar


T = TypeVar("T")


class RuntimeAlias:
    def __init__(self, origin: type[Foo[Any]], args: tuple[Any, ...]) -> None:
        self.origin = origin
        self.args = args

    def __call__(self, *values: Any) -> Foo[Any]:
        if len(self.args) == 2 and self.args[-1] is ...:
            item_type = self.args[0]
            if any(not isinstance(value, item_type) for value in values):
                raise TypeError("element type mismatch")
        return self.origin(*values)


class Foo(Generic[T]):
    def __class_getitem__(cls, params: Any) -> Any:
        args = params if isinstance(params, tuple) else (params,)
        return RuntimeAlias(cls, args)

    def __init__(self, *values: Any) -> None:
        self.values = values


alias = Foo[int, ...]
good = alias(1, 2, 3)
bad_error = None
try:
    alias(1, "wrong")
except TypeError as exc:
    bad_error = str(exc)

if TYPE_CHECKING:
    annotated: Foo[int, ...] = good
    reveal_type(alias)
    reveal_type(good)

print(json.dumps({
    "alias_args": [repr(item) for item in alias.args],
    "bad_error": bad_error,
    "values": list(good.values),
}, sort_keys=True))
