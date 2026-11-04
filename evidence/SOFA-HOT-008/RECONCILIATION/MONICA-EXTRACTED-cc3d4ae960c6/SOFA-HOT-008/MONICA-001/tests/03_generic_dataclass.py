#!/usr/bin/env python3
"""Runtime audit of generic dataclass defaults; static checker intentionally not assumed installed."""
from __future__ import annotations
import json
from dataclasses import dataclass, field
from typing import Callable, Generic, TypeVar

@dataclass
class C: pass
@dataclass
class C2(C): pass
CT = TypeVar('CT', bound=C)

@dataclass
class Unsound(Generic[CT]):
    var: CT = field(default_factory=lambda: C())  # runtime permits base C for a claimed CT

@dataclass
class UnsoundChild(Unsound[C2]):
    pass

@dataclass
class Sound(Generic[CT]):
    var: CT

@dataclass
class SoundChild(Sound[C2]):
    var: C2 = field(default_factory=C2)

def make_sound(factory: Callable[[], CT]) -> Sound[CT]:
    return Sound(factory())

def main() -> None:
    bad: UnsoundChild = UnsoundChild()
    assert type(bad.var) is C and not isinstance(bad.var, C2)
    good_child = SoundChild()
    good_base = make_sound(C)
    good_c2 = make_sound(C2)
    assert type(good_child.var) is C2 and type(good_base.var) is C and type(good_c2.var) is C2
    print(json.dumps({'case_id':'fa8ac823-1616-4df3-9f73-feaa8b5b4bf7','execution':'CPython runtime; no installed static checker','assertions':4,'negative_control':{'name':'inherited_base_default_for_CT_C2','minimized_input':'UnsoundChild()','promised':'C2','actual_type':type(bad.var).__name__,'detected':True},'result':'A lambda and type-ignore do not repair the runtime or declared generic invariant; they silence/check around it. Sound alternatives require a value/factory from the caller or a concrete subclass override.','checker_status':'NOT_TESTED: mypy and pyright absent; no checker was installed.'},indent=2))
if __name__=='__main__': main()
