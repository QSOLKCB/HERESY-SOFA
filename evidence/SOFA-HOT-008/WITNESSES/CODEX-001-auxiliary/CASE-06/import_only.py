from typing import GenericAlias, get_origin, get_args
from types import GenericAlias as PublicGenericAlias
print(GenericAlias is PublicGenericAlias)
