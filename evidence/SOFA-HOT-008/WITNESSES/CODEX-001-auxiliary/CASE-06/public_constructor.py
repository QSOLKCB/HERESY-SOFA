from types import GenericAlias
from typing import get_args,get_origin
a = GenericAlias(tuple, (int, ...))
print(get_origin(a) is tuple, get_args(a))
print(a((1,2)))
