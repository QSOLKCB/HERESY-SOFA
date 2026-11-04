import importlib.util
from pathlib import Path
import runpy
import sys
from types import GenericAlias
from typing import get_args,get_origin
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import Evidence

e=Evidence(6)
original=e.folder/'source-a66cf887-724d-41f9-843f-d0d9548b0b84-block-01.py'
r=e.run([sys.executable,str(original)])
e.check('reply_verbatim_exit',r['exit_code'],1,kind='negative')
experiments={
 'import_only.py':'from typing import GenericAlias, get_origin, get_args\nfrom types import GenericAlias as PublicGenericAlias\nprint(GenericAlias is PublicGenericAlias)\n',
 'subscript_only.py':'from typing import GenericAlias\nT = GenericAlias[tuple[int, ...]]\n',
 'class_only.py':'from typing import GenericAlias\nclass Foo(GenericAlias[tuple[int, ...]]):\n    def __init__(self, *values: int) -> None:\n        self.values = values\n',
 'public_constructor.py':'from types import GenericAlias\nfrom typing import get_args,get_origin\na = GenericAlias(tuple, (int, ...))\nprint(get_origin(a) is tuple, get_args(a))\nprint(a((1,2)))\n',
}
for name,code in experiments.items():
    path=e.folder/name;path.write_text(code)
    r=e.run([sys.executable,str(path)])
    expected=1 if name in ('subscript_only.py','class_only.py') else 0
    e.check(name+'_exit',r['exit_code'],expected,kind='negative' if expected else 'positive')
    if expected: e.check(name+'_TypeError',"not subscriptable" in r['stderr'],True,kind='negative')
e.check('constructor_origin',get_origin(GenericAlias(tuple,(int,...))) is tuple,True)
e.check('constructor_args',get_args(GenericAlias(tuple,(int,...)))==(int,...),True)
e.check('ordinary_class_not_alias',get_origin(type('Ordinary',(),{})),None,kind='negative')
main=runpy.run_path(str(e.folder/'source-0b3591f6-75de-4661-a7a7-ec28193e1518-block-02.py'))
Foo=main['Foo']
e.check('custom_homogeneous_positive',Foo[int,...](1,2,3)._values,(1,2,3))
for name,fn,expected_type in [('wrong_homogeneous',lambda:Foo[int,...](1,'x'),'TypeError'),
                              ('arity',lambda:Foo[int,str](1),'TypeError'),
                              ('empty_subscription',lambda:Foo[()],'IndexError')]:
    try: fn()
    except Exception as exc:
        e.data.setdefault('exceptions',[]).append(dict(test=name,type=type(exc).__name__,message=str(exc)))
        e.check(name,type(exc).__name__,expected_type,kind='negative')
    else: e.check(name,'no exception',expected_type,kind='negative')
e.check('custom_heterogeneous_wrong_types_accepted',Foo[int,str]('x',1)._values,('x',1),kind='negative')
e.check('custom_repr',repr(Foo[int,...]),'Foo[int, ...]')
e.check('custom_parameters_hold_concrete_args',Foo[int,...].__parameters__==(int,...),True,kind='negative')
e.run([sys.executable,str(e.folder/'corrected.py')])
e.data['limitations']=[dict(label='NOT_TESTED',claim='All Pyright diagnostics, inference and 1.1.414 claims',reason='No Pyright executable/module installed; Node/NPM not invoked'),
 dict(label='UNSUPPORTED',claim='Assigning instance __parameters__ makes Pyright infer this alias, or the proposed GenericAlias subscript keeps static checking clean'),
 dict(label='INFERRED',claim='Use the public types.GenericAlias(origin,args) constructor for runtime metadata only; prefer separate Fixed/Variadic classes for a checker-oriented API, pending checker validation.')]
e.finish()
