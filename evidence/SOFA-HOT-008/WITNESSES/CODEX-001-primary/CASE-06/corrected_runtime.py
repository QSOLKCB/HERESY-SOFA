"""What types.GenericAlias actually provides at runtime."""

from types import GenericAlias


class RuntimeFoo:
    def __init__(self, *values):
        self.values = values


runtime_alias = GenericAlias(RuntimeFoo, (int, ...))
tuple_alias = GenericAlias(tuple, (int, ...))
