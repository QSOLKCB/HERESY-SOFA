import importlib.metadata as metadata
import importlib.util
import json
import os
import platform
from pathlib import Path
import shutil
import sys
from common import ROOT, command, utc

data = dict(execution_utc=utc(), os=platform.platform(), architecture=platform.machine(),
            uname=list(platform.uname()), python=sys.version, python_implementation=platform.python_implementation(),
            executable=sys.executable, recursion_limit=sys.getrecursionlimit(),
            affinity_cpus=sorted(os.sched_getaffinity(0)),
            context_date='2026-11-05', context_timezone='Australia/Adelaide',
            clock_note='Workstation date is 2026-11-04 UTC; receipt timestamps use the workstation clock.',
            dependencies={}, commands=[], network_experiments='None; fake services only',
            scope='System interpreter /usr/bin/python3; no environments or dependencies installed')
for package in ['yt-dlp', 'openpyxl', 'mypy', 'pyright']:
    module = package.replace('-', '_')
    spec = importlib.util.find_spec(module)
    try:
        version = metadata.version(package)
    except metadata.PackageNotFoundError:
        version = None
    data['dependencies'][package] = dict(version=version, module_path=spec.origin if spec else None,
                                        executable=shutil.which(package))
for argv in [['uv','--version'], ['uname','-a'], ['lscpu'], ['cat','/etc/os-release'],
             ['mypy','--version'], ['curl','--version'], ['bash','--version'], ['rg','--version'],
             ['uv','python','list','--only-installed'], ['git','-C',str(ROOT),'rev-parse','--show-toplevel']]:
    data['commands'].append(command(argv))
(ROOT/'environment.json').write_text(json.dumps(data,indent=2)+'\n')
print(json.dumps(data,indent=2))
