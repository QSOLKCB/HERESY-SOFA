"""Diff3 ancestry leak: real disposable Git merge; compare bad vs safe parser."""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

CLAIMS = ("diff3_contains_fourth_marker", "naive_resolver_keeps_ancestor",
          "mitigation_excludes_ancestor", "mitigation_removes_all_conflict_markers")

def out(checks, git_version="not_available"):
    passed = bool(checks) and all(checks.values())
    print(json.dumps({"claims": {k: "executed" if passed else "not_tested" for k in CLAIMS},
                      "observations": {"checks": checks, "git_version": git_version,
                        "all_checks_passed": passed, "mode": "temporary git merge, no real repository touched"},
                      "mitigation": "Parse diff3's ||||||| ancestor separator before unioning sides; reject remaining conflict markers."},sort_keys=True))
    return 0 if passed else 1

def run(exe, cwd, env, *args, expected=0):
    p = subprocess.run([exe, "-C", str(cwd), *args], env=env, capture_output=True,
                       text=True, timeout=8, check=False)
    if p.returncode != expected:
        raise RuntimeError("git {} unexpected exit {}".format(args[0],p.returncode))
    return p.stdout

def main():
    exe = shutil.which("git")
    if exe is None:
        return out({})
    version = subprocess.run([exe,"--version"], capture_output=True,text=True,timeout=5)
    if version.returncode != 0 or not version.stdout.startswith("git version "):
        return out({})
    env = os.environ.copy()
    for k in list(env):
        if k.startswith("GIT_"):
            env.pop(k, None)
    env["GIT_CONFIG_NOSYSTEM"]="1"
    env["GIT_CONFIG_GLOBAL"]=os.devnull
    with tempfile.TemporaryDirectory(prefix="heresy-diff3-") as tmp:
        root=Path(tmp)/"disposable repo"
        root.mkdir()
        run(exe,root,env,"init","-q")
        run(exe,root,env,"config","user.name","Fixture")
        run(exe,root,env,"config","user.email","fixture@example.invalid")
        run(exe,root,env,"config","merge.conflictStyle","diff3")
        base_branch = run(exe,root,env,"branch","--show-current").strip()
        file=root/"notes.txt"
        file.write_text("common header\nancestor sentence\ncommon footer\n")
        run(exe,root,env,"add","notes.txt")
        run(exe,root,env,"commit","-qm","base")
        run(exe,root,env,"branch","other")
        file.write_text("common header\nours sentence\ncommon footer\n")
        run(exe,root,env,"commit","-qam","ours")
        run(exe,root,env,"checkout","-q","other")
        file.write_text("common header\ntheirs sentence\ncommon footer\n")
        run(exe,root,env,"commit","-qam","theirs")
        run(exe,root,env,"checkout","-q",base_branch)
        # git checkout should return to original branch, which may be master or main.
        run(exe,root,env,"merge","other",expected=1)
        lines=file.read_text().splitlines(keepends=True)
        starts=[i for i,x in enumerate(lines) if x.startswith("<<<<<<< ")]
        bases=[i for i,x in enumerate(lines) if x.startswith("||||||| ")]
        middles=[i for i,x in enumerate(lines) if x.strip()=="======="]
        ends=[i for i,x in enumerate(lines) if x.startswith(">>>>>>> ")]
        if not (len(starts)==len(bases)==len(middles)==len(ends)==1):
            raise RuntimeError("expected one diff3 conflict")
        a,b,c,d=starts[0],bases[0],middles[0],ends[0]
        if not a<b<c<d:raise RuntimeError("bad marker order")
        naive="".join(lines[:a]+lines[a+1:c]+lines[c+1:d]+lines[d+1:])
        repaired="".join(lines[:a]+lines[a+1:b]+lines[c+1:d]+lines[d+1:])
        marker=re.compile(r"^(<<<<<<< |\|\|\|\|\|\|\| |=======\s*$|>>>>>>> )",re.M)
        checks={
            "diff3_contains_fourth_marker": "||||||| " in "".join(lines),
            "naive_resolver_keeps_ancestor": "ancestor sentence" in naive and "||||||| " in naive,
            "naive_three_marker_scan_misses_base": not re.search(r"^(<<<<<<< |=======\s*$|>>>>>>> )",naive,re.M),
            "mitigation_excludes_ancestor": "ancestor sentence" not in repaired and "ours sentence" in repaired and "theirs sentence" in repaired,
            "mitigation_removes_all_conflict_markers": not marker.search(repaired),
        }
        return out(checks,version.stdout.strip())

if __name__=="__main__":
    try:sys.exit(main())
    except (OSError,RuntimeError,subprocess.TimeoutExpired) as exc:
        print("HERESY-007: {}".format(type(exc).__name__),file=sys.stderr)
        sys.exit(1)