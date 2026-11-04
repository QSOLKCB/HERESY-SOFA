from typing import GenericAlias, get_origin, get_args

# Create a generic alias that accepts an ellipsis as the last argument
T = GenericAlias[tuple[int, ...]]

# Use it like `Foo[int, ...]`
class Foo(GenericAlias[tuple[int, ...]]):
    def __init__(self, *values: int) -> None:
        self.values = values

# Inspect at runtime
print(get_origin(Foo))
print(get_args(Foo))
