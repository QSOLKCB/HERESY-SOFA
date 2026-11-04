from typing import Generic, TypeVar, Unpack, TypeVarTuple

T = TypeVar("T")
Ts = TypeVarTuple("Ts")


class Fixed(Generic[Unpack[Ts]]):
    def __init__(self, *values: Unpack[Ts]) -> None:
        self.values = values


class Variadic(Generic[T]):
    def __init__(self, *values: T) -> None:
        self.values = values


a = Fixed[int, str](1, "cabbage")   # ok, checker sees the exact pack
b = Variadic[int](1, 2, 3, 4)       # ok, checker sees the element type
