import importlib.util
from pathlib import Path
import runpy
import sys
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import Evidence

e=Evidence(3)
original=e.folder/'source-fa8ac823-1616-4df3-9f73-feaa8b5b4bf7-block-01.py'
e.run([sys.executable,str(original)])
scope=runpy.run_path(str(original))
C,C2,Box=scope['C'],scope['C2'],scope['myclass']
e.check('unparameterized_default',type(Box().var).__name__,'C')
e.check('subclass_override',type(scope['myclass_child']().var).__name__,'C2')
e.check('parameterized_default_is_C2',isinstance(Box[C2]().var,C2),False,kind='negative')
e.check('parameterized_explicit_value_is_C2',isinstance(Box[C2](C2()).var,C2),True)
e.check('factory_allocates_separate_instances',Box().var is Box().var,False)
sound=runpy.run_path(str(e.folder/'corrected.py'))
e.check('explicit_factory_C2',type(sound['from_factory'](sound['C2']).var).__name__,'C2')
try: sound['Box']()
except TypeError as exc:
    e.data['required_field_exception'] = dict(type=type(exc).__name__,message=str(exc))
    e.check('required_field_omission_rejected',True,True,kind='negative')
else: e.check('required_field_omission_rejected',False,True,kind='negative')

variants={
 'annotated_ignore.py':original.read_text().replace('a = myclass()','a: myclass[C] = myclass()'),
 'lambda_no_ignore.py':original.read_text().replace('  # type: ignore[assignment]','').replace('a = myclass()','a: myclass[C] = myclass()'),
 'direct_factory.py':original.read_text().replace('lambda: C())  # type: ignore[assignment]','C)').replace('a = myclass()','a: myclass[C] = myclass()'),
 'wrong_required.py':'from corrected import Box, C, C2\nx: Box[C2] = Box(C())\n',
 'ignored_counterexample.py':original.read_text().replace('a = myclass()','a: myclass[C2] = myclass[C2]()')+'\nassert isinstance(a.var, C2), "typed C2 field actually contains C"\n',
}
for name,code in variants.items(): (e.folder/name).write_text(code)
counter=e.run([sys.executable,str(e.folder/'ignored_counterexample.py')])
e.check('minimal_counterexample_exit',counter['exit_code'],1,kind='negative')
e.check('minimal_counterexample_assertion', 'typed C2 field actually contains C' in counter['stderr'], True,kind='negative')
if importlib.util.find_spec('mypy'):
    import importlib.metadata
    e.data['mypy_version']=importlib.metadata.version('mypy')
    with tempfile.TemporaryDirectory(prefix='codex008-mypy-') as cache:
        for name in [original.name,'annotated_ignore.py','lambda_no_ignore.py','direct_factory.py','corrected.py','wrong_required.py','ignored_counterexample.py']:
            r=e.run([sys.executable,'-m','mypy','--no-incremental','--cache-dir',cache,name],cwd=e.folder)
            e.check('mypy_default_'+name,r['exit_code'],0 if name in ('annotated_ignore.py','corrected.py','ignored_counterexample.py') else 1,
                    kind='negative' if name not in ('annotated_ignore.py','corrected.py') else 'positive')
        for name in ['annotated_ignore.py','corrected.py']:
            r=e.run([sys.executable,'-m','mypy','--strict','--no-incremental','--cache-dir',cache,name],cwd=e.folder)
            e.check('mypy_strict_'+name,r['exit_code'],0)
else: e.data['limitations'].append(dict(label='NOT_TESTED',claim='mypy execution'))
e.data['limitations'].append(dict(label='NOT_TESTED',claim='Nincompoop exact mypy 2.3.1 / Python 3.14 combination; installed mypy is a different version'))
e.finish()
