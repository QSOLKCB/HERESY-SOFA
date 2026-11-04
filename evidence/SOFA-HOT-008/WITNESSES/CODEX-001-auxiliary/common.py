"""Local evidence helpers. No network access or dependency installation."""
import datetime as dt
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
SEED = 26051108

def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat()

def command(argv, *, cwd=None, env=None, timeout=30):
    started = utc()
    try:
        p = subprocess.run(argv, cwd=cwd, env=env, text=True, capture_output=True, timeout=timeout)
        return dict(argv=argv, cwd=str(cwd or Path.cwd()), started_utc=started,
                    finished_utc=utc(), exit_code=p.returncode, stdout=p.stdout, stderr=p.stderr)
    except subprocess.TimeoutExpired as e:
        return dict(argv=argv, started_utc=started, finished_utc=utc(), exit_code=None,
                    exception=repr(e), stdout=str(e.stdout or ''), stderr=str(e.stderr or ''))

class Evidence:
    def __init__(self, case):
        self.folder = ROOT / f'CASE-{case:02}'
        self.data = dict(case=case, started_utc=utc(), python=sys.version,
                         executable=sys.executable, seed=SEED, checks=[], commands=[], limitations=[])

    def check(self, name, actual, expected, *, kind='positive', label='EXECUTED'):
        passed = actual == expected
        self.data['checks'].append(dict(name=name, kind=kind, label=label,
                                       expected=expected, actual=actual, passed=passed))
        return passed

    def run(self, argv, **kwargs):
        r = command(argv, **kwargs)
        self.data['commands'].append(r)
        return r

    def finish(self):
        self.data['finished_utc'] = utc()
        self.data['all_checks_passed'] = all(c['passed'] for c in self.data['checks'])
        path = self.folder / 'receipt.json'
        with path.open('x') as f:
            json.dump(self.data, f, indent=2, sort_keys=True)
            f.write('\n')
        print(json.dumps(dict(case=self.data['case'], checks=len(self.data['checks']),
                              all_checks_passed=self.data['all_checks_passed'])))
        if not self.data['all_checks_passed']:
            raise SystemExit(1)
