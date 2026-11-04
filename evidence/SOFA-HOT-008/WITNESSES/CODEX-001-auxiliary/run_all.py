"""Run each independent case in a fresh offline system-Python subprocess."""
import json
import os
from pathlib import Path
import sys
from common import ROOT,command,utc

os.environ['PYTHONDONTWRITEBYTECODE']='1'
cases=[int(x) for x in sys.argv[1:]] or list(range(1,9))
failed=[]
for case in cases:
    folder=ROOT/f'CASE-{case:02}'
    if (folder/'receipt.json').exists():
        raise SystemExit(f'Refusing to overwrite evidence: {folder}/receipt.json')
    argv=['uv','run','--no-project','--offline','--no-managed-python','--python','/usr/bin/python3','python','-B',str(folder/'test.py')]
    result=command(argv,cwd=ROOT,timeout=180)
    with (folder/'execution.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(dict(case=case,exit_code=result['exit_code'],stdout=result.get('stdout'),stderr=result.get('stderr'))),flush=True)
    if result['exit_code']!=0:failed.append(case)
raise SystemExit(bool(failed))
