# HERESY-008 — The Git Identity Crisis

**Case classification:** PEBKAC · Layer 8 · ID-10-T (satirical classification)  
**Disposition:** Git acquitted; operator configuration at fault  
**Evidence:** [Executable reproduction](../experiments/HERESY-008/run.py) · [experiment protocol](../experiments/HERESY-008/experiment.md)  
**Date:** 2026-11-01

## Allegation

A batch wrapper called Git with a checkout selected by `-C`, but previously set `GIT_DIR` to what the author believed was the Git *installation* directory:

```bat
set "GIT_DIR=D:\tools\git"
"D:\tools\git\bin\git.exe" -C "D:\work\fpc_trunk" pull
```

`GIT_DIR` is **not** an application-defined variable for the Git executable. Git documents it as an override for the **repository metadata directory**. `-C` changes the working directory but does not cancel the environment override.

This is not evidence of a defect in Git. It is an operator-defined variable colliding with Git's documented control interface.

## Why this can be worse than an error message

An invalid `GIT_DIR` can cause an immediate fatal error. But if it names **another valid repository**, the command can **succeed against the wrong index**.

The disposable Python/Git experiment creates two unrelated repositories, in directories containing spaces, and commits different `marker.txt` content to each. It then runs `git -C <target> ...` with `GIT_DIR` pointing to the other repository.

Expected by the operator: `-C` unambiguously selects the target checkout.

**Actually observed on Linux with Git 2.47.3:** `rev-parse --absolute-git-dir` selects the *other* repository's metadata; `status` reports the target's file as changed; `git add marker.txt` exits zero and updates the *other* repository's index with the target's file content. The intended repository's index remains unchanged. Removing `GIT_DIR` restores the correct repository identity.

Seven explicit assertions must pass before the script emits `executed` claims. A missing Git executable or failed child command returns a failed run, not a green receipt. No user's actual repositories are touched.

## Mitigation

For ordinary development, clone the repository and work inside its checkout. If a Windows launcher genuinely requires a Git installation path, use `GIT_INSTALL_DIR` or `GIT_EXE`, not `GIT_DIR`. Clear unintended inherited overrides and inspect `git rev-parse --absolute-git-dir` before running mutations when the environment may be contaminated.

Illustrative Windows wrapper (**not Windows-executed**):

```bat
@echo off
setlocal
set "GIT_DIR="
set "GIT_EXE=D:\tools\git\bin\git.exe"
"%GIT_EXE%" -C "D:\work\fpc_trunk" rev-parse --absolute-git-dir
if errorlevel 1 exit /b 1
rem Compare the reported path with the expected repository before changing anything.
```

Clearing `GIT_DIR` alone is not a universal sanitization step: `GIT_WORK_TREE`, `GIT_INDEX_FILE` and `GIT_COMMON_DIR` can also alter Git behaviour. Preserve intentional overrides and validate the intended repository's identity.

## Evidence boundary

**Executed:** local Linux Python 3 + Git 2.47.3, two disposable repositories, seven assertions, environment-correction check.  
**Not tested:** original user's machine, Windows `cmd.exe`, network `git pull`, actual third-party repositories.  
**Not claimed:** the original reporter staged anything into the wrong repository. We independently demonstrated a possible consequence of the same configuration mistake.

## Verdict

> Git is acquitted. The operator is sentenced to thirty days of reading `git help environment` without access to Stack Overflow.

**The software followed the more explicit instruction. The conflicting instruction came from the chair.**

*The PEBKAC label describes a class of configuration mistake, not the intelligence or identity of an individual.*