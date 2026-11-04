"""Copy inputs to a fresh /tmp directory and reproduce without changing sealed evidence."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

source=Path(__file__).resolve().parent
target=Path(tempfile.mkdtemp(prefix='SOFA-HOT-008-reproduction-'))/'CODEX-001'
target.mkdir()
for name in ['common.py','run_all.py']:
    shutil.copyfile(source/name,target/name)
for folder in sorted(source.glob('CASE-*')):
    destination=target/folder.name;destination.mkdir()
    for file in folder.iterdir():
        if file.is_file() and (file.suffix in ('.py','.sh') or file.name in ('source.json','snippet-manifest.json')):
            shutil.copyfile(file,destination/file.name)
base=['uv','run','--no-project','--offline','--no-managed-python','--python','/usr/bin/python3','python','-B']
commands=[base+['run_all.py'],base+['CASE-04/shell_controls.py'],base+['CASE-04/mock_shell_controls.py'],base+['CASE-08/state_space.py']]
results=[]
for argv in commands:
    p=subprocess.run(argv,cwd=target,text=True,capture_output=True)
    results.append(dict(argv=argv,exit_code=p.returncode,stdout=p.stdout,stderr=p.stderr))
(target/'reproduction-run.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(dict(reproduction_directory=str(target),commands=[dict(argv=r['argv'],exit_code=r['exit_code']) for r in results]),indent=2))
raise SystemExit(any(r['exit_code']!=0 for r in results))
