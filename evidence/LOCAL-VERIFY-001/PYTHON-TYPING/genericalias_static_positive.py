"""A checker-clean TypeVarTuple baseline without a literal ellipsis."""

from typing import Generic, TypeVarTuple


Ts = TypeVarTuple("Ts")


class Packed(Generic[*Ts]):
    pass


one: Packed[int] = Packed()
many: Packed[int, str, int] = Packed()
repeated: Packed[int, int, int] = Packed()
