"""Runtime GenericAlias constructor demonstration; not static-checker evidence."""
from types import GenericAlias
from typing import get_args, get_origin

class Foo:
    def __init__(self,*values):
        self.values=values
    def __class_getitem__(cls,args):
        return GenericAlias(cls,args)

alias=Foo[int,...]
assert get_origin(alias) is Foo
assert get_args(alias)==(int,Ellipsis)
assert alias(1,2).values==(1,2)
# GenericAlias records metadata; it does NOT validate constructor arguments.
assert alias('not an int').values==('not an int',)
