"""Correct runtime GenericAlias constructor and its non-enforcement boundary."""

from __future__ import annotations

import json
from types import GenericAlias
from typing import TYPE_CHECKING, get_args, get_origin


alias = GenericAlias(tuple, (int, Ellipsis))
value = alias((1, "unchecked"))

if TYPE_CHECKING:
    reveal_type(alias)
    reveal_type(value)

print(json.dumps({
    "args": [repr(item) for item in get_args(alias)],
    "origin": repr(get_origin(alias)),
    "repr": repr(alias),
    "runtime_type": f"{type(alias).__module__}.{type(alias).__qualname__}",
    "unchecked_value": list(value),
}, sort_keys=True))
