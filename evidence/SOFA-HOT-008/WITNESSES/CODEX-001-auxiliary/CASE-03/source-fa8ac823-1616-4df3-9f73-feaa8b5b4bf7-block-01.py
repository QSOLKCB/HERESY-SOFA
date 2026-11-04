from __future__ import annotations
from dataclasses import dataclass, field
from typing import Generic, TypeVar

@dataclass
class C:
    pass

@dataclass
class C2(C):
    pass

CT = TypeVar("CT", bound=C)

@dataclass
class myclass(Generic[CT]):
    # lambda (not `C`) so the factory is typed as Callable[[], CT] for each CT
    var: CT = field(default_factory=lambda: C())  # type: ignore[assignment]

@dataclass
class myclass_child(myclass[C2]):
    var: C2 = field(default_factory=C2)

a = myclass()
b = myclass_child()
print(type(a.var), type(b.var))   # <class 'C'> <class 'C2'>
