"""TypeVarTuple runtime metadata versus static literal-ellipsis handling."""

from __future__ import annotations

import json
from typing import Generic, TYPE_CHECKING, TypeVarTuple, get_args


Ts = TypeVarTuple("Ts")


class Packed(Generic[*Ts]):
    pass


ordinary_alias = Packed[int, str]
ellipsis_alias = Packed[int, ...]
ellipsis_only_alias = Packed[...]

ordinary = ordinary_alias()
with_ellipsis = ellipsis_alias()
ellipsis_only = ellipsis_only_alias()

if TYPE_CHECKING:
    reveal_type(ordinary)
    reveal_type(with_ellipsis)
    reveal_type(ellipsis_only)

print(json.dumps({
    "ellipsis_args": [repr(item) for item in get_args(ellipsis_alias)],
    "ellipsis_only_args": [repr(item) for item in get_args(ellipsis_only_alias)],
    "ordinary_args": [repr(item) for item in get_args(ordinary_alias)],
}, sort_keys=True))
