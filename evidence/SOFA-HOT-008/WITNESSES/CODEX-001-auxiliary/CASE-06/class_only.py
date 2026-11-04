from typing import GenericAlias
class Foo(GenericAlias[tuple[int, ...]]):
    def __init__(self, *values: int) -> None:
        self.values = values
