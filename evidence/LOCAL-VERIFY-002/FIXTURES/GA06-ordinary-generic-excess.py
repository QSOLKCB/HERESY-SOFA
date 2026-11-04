"""Ordinary one-TypeVar generic supplied with two arguments."""

from typing import Generic, TypeVar


T = TypeVar("T")


class Single(Generic[T]):
    pass


invalid_alias = Single[int, str]
print(invalid_alias)
