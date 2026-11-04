from typing import Any, Generic, TypeVar

T = TypeVar("T")


class _FooAlias:
    def __init__(self, args: tuple[Any, ...]) -> None:
        self._args = args
        self.__parameters__ = args

    def __call__(self, *values: Any) -> "Foo[Any]":
        if self._args[-1] is ...:
            item = self._args[0]
            if any(not isinstance(v, item) for v in values):
                raise TypeError(f"expected all {item.__name__}")
        elif len(values) != len(self._args):
            raise TypeError(f"expected {len(self._args)} values")
        return Foo(*values)

    def __repr__(self) -> str:
        inner = ", ".join("..." if a is ... else a.__name__ for a in self._args)
        return f"Foo[{inner}]"


class Foo(Generic[T]):
    def __class_getitem__(cls, params: Any) -> Any:
        params = params if isinstance(params, tuple) else (params,)
        if params[-1] is ... and len(params) != 2:
            raise TypeError("Ellipsis must follow exactly one type argument")
        return _FooAlias(params)

    def __init__(self, *values: Any) -> None:
        self._values = values
