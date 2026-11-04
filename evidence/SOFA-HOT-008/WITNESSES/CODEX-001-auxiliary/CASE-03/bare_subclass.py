from dataclasses import dataclass,field
from typing import Generic,TypeVar

@dataclass
class C:
    pass

T=TypeVar('T',bound=C)

@dataclass
class Base(Generic[T]):
    var:T=field(default_factory=C)  # type: ignore[assignment]

class Bare(Base):
    pass

class Bound(Base[C]):
    pass

reveal_type(Bare().var)
reveal_type(Bound().var)
