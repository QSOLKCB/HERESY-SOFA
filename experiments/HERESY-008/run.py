"""HERESY-008: operator-set GIT_DIR selects another repo's index.

Uses only newly created disposable local repositories. No network or Windows execution.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

CLAIMS = (
    "git_dir_overrides_repository_discovery",
    "wrong_repository_index_staged_successfully",
    "intended_repository_index_unchanged",
    "removing_override_restores_expected_repository",
)

def emit(checks, version, supported=True):
    passed = bool(checks) and all(checks.values())
    print(json.dumps({
        "claims": {name: ("executed" if passed else
                          "not_tested" if supported else "unsupported")
                   for name in CLAIMS},
        "observations": {
            "git_version": version, "checks": checks,
            "all_checks_passed": passed,
            "windows_cmd_executed": False,
            "environment": "disposable local repositories",
        },
        "mitigation": "Use GIT_INSTALL_DIR for the executable; keep GIT_DIR unset for "
                      "ordinary checkouts; check git -C <checkout> rev-parse "
                      "--absolute-git-dir before mutating.",
    }, sort_keys=True))
    return 0 if passed else 1

def git(exe, cwd, env, *args):
    proc = subprocess.run(
        [exe, "-C", str(cwd), *args], env=env,
        capture_output=True, text=True, timeout=10, check=False
    )
    if proc.returncode:
        raise RuntimeError("git {} exited {}".format(args[0], proc.returncode))
    return proc.stdout

def main():
    exe = shutil.which("git")
    if exe is None:
        return emit({}, "unavailable", supported=False)
    version = subprocess.run([exe, "--version"], capture_output=True,
                             text=True, timeout=5, check=False)
    if version.returncode or not version.stdout.startswith("git version "):
        return emit({}, "unavailable", supported=False)
    env = os.environ.copy()
    for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE",
                "GIT_NAMESPACE", "GIT_CONFIG", "GIT_CONFIG_COUNT",
                "GIT_CONFIG_GLOBAL", "GIT_CONFIG_SYSTEM"):
        env.pop(key, None)
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    with tempfile.TemporaryDirectory(prefix="heresy-008-") as root:
        target = Path(root) / "target checkout"
        other = Path(root) / "other repository"
        for repo, label in ((target, "target"), (other, "other")):
            repo.mkdir()
            git(exe, repo, env, "init", "-q")
            git(exe, repo, env, "config", "user.name", "Local Tester")
            git(exe, repo, env, "config", "user.email", "test@example.invalid")
            (repo / "marker.txt").write_text(
                "content from {}\n".format(label), encoding="utf-8"
            )
            git(exe, repo, env, "add", "marker.txt")
            git(exe, repo, env, "commit", "-qm", "baseline")

        wrong_env = dict(env, GIT_DIR=str(other / ".git"))
        wrong_meta = git(exe, target, wrong_env, "rev-parse",
                         "--absolute-git-dir").strip()
        wrong_status = git(exe, target, wrong_env, "status", "--short")
        git(exe, target, wrong_env, "add", "marker.txt")
        other_index = git(exe, other, env, "show", ":marker.txt")
        target_index = git(exe, target, env, "show", ":marker.txt")
        restored = git(exe, target, env, "rev-parse",
                       "--absolute-git-dir").strip()
        target_status = git(exe, target, env, "status", "--porcelain")
        checks = {
            "wrong_metadata_selected": wrong_meta == str((other / ".git").resolve()),
            "wrong_status_reports_changed_file": "M marker.txt" in wrong_status,
            "wrong_add_exited_zero": True,  # git() rejects nonzero statuses.
            "wrong_index_has_target_content": other_index == "content from target\n",
            "correct_index_retains_target_content": target_index == "content from target\n",
            "clearing_override_selects_target": restored == str((target / ".git").resolve()),
            "target_checkout_is_still_clean": target_status == "",
        }
        return emit(checks, version.stdout.strip())

if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print("HERESY-008: {}".format(type(exc).__name__), file=sys.stderr)
        sys.exit(1)
