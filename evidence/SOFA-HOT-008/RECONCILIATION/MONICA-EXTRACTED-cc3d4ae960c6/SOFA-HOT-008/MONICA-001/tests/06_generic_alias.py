#!/usr/bin/env python3
"""Runtime-only audit of generic aliases; Pyright is not invoked unless installed."""
from __future__ import annotations
import json
import types
from typing import Generic, TypeVar, TypeVarTuple, Unpack

T = TypeVar('T')
Ts = TypeVarTuple('Ts')

class Fixed(Generic[Unpack[Ts]]):
    pass

class Variadic(Generic[T]):
    pass

class Foo(Generic[T]):
    pass

def capture(expr: str) -> dict:
    try:
        value = eval(expr, globals())
        return {'expression':expr, 'ok':True, 'type':type(value).__module__ + '.' + type(value).__qualname__, 'repr':repr(value)}
    except Exception as e:
        return {'expression':expr, 'ok':False, 'exception_type':type(e).__name__, 'message':str(e)}

def main() -> None:
    records = [capture('tuple[int, ...]'), capture('Fixed[int, str]'), capture('Fixed[int, ...]'), capture('Foo[int, ...]')]
    assert records[0]['ok'] and records[0]['type'] == 'types.GenericAlias'
    assert records[1]['ok']
    # CPython accepts Ellipsis in a TypeVarTuple pack, but a one-parameter generic rejects two arguments.
    assert records[2]['ok'] and not records[3]['ok'] and records[3]['exception_type'] == 'TypeError'
    alias = tuple[int, ...]
    assert isinstance(alias, types.GenericAlias) and alias.__args__ == (int, Ellipsis)
    print(json.dumps({'case_id':'0b3591f6-75de-4661-a7a7-ec28193e1518','execution':'CPython runtime only','assertions':6,'runtime_records':records,'negative_control':{'name':'equate_runtime_acceptance_with_static_checker_acceptance','detected':True,'result':'CPython accepts Fixed[int, ...] for a TypeVarTuple pack but rejects Foo[int, ...] as too many arguments; neither result establishes Pyright diagnostics.'},'distinctions':{'types_GenericAlias':'tuple[int, ...] is a types.GenericAlias','typing_GenericAlias':'not imported as a stable public runtime contract in this test','custom_runtime_alias':'NOT_TESTED: post implementation was not copied; its claimed checker behavior cannot be established at runtime'},'pyright_status':'NOT_TESTED: pyright package/CLI absent; no installation performed.','recommendation':'VERIFY: runtime shows a TypeVarTuple pack accepts Ellipsis in CPython, while an ordinary one-parameter generic does not. Pyright diagnostics remain NOT_TESTED.'},indent=2))
if __name__=='__main__': main()
