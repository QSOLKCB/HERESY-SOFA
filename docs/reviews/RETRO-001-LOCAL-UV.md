# RETRO-001 — Local UV Verification Audit

**Recorded:** 4 November 2026 · **Status:** `PASS` for a bounded, independent local verification · **Publication:** [Retro Systems Gauntlet SOFA question](https://agents.stackoverflow.com/questions/c5fa3bff-959c-4c28-bcaa-68dd8415697e) and published verification reply ID `b607d7f6-ce7d-43d1-9a32-2cb23317e28d`.

## Immutable execution identity

- Source: merged PR #11 / `main` commit `5e3825f93885579f086f8d3650f07cd64b530632`.
- Uploaded sanitized report: [RETRO-001-LOCAL-UV-REPORT.json](../../evidence/RETRO-GAUNTLET-001/RETRO-001-LOCAL-UV-REPORT.json).
- Report SHA-256: `8933631a60676f427407a2f6c431defc8f07480642d1903dbb4ed32ad7c160f2`.
- Original Git blob SHA-1 of report: `4ae5bf2f62e8679bb32e574b572fc93efb7cc3ee`, confirming the committed bytes match the uploaded file.
- Independent checks: compared the uploaded digest with the actual report bytes and its three recorded source SHA-256 hashes against the exact pinned GitHub commit; all matched. This audit **does not** independently reproduce the workstation's operating-system or process observations.

## Environment and executed checks

Ubuntu 26.04.1 LTS; Linux 7.0.0-42-generic x86_64; CPython 3.14.4; uv 0.12.1. The operator's tool created a fresh external uv-managed venv from the existing system interpreter and executed test commands with `uv run --no-project --offline`; no pip installation or additional runtime dependencies were needed. Git synchronization happened before the offline test runs.

| Check | Recorded observation | Interpretation |
| --- | --- | --- |
| Targeted tests | 6 passed, 0 failed | All declared RETRO-001 controls passed locally |
| Whole unittest suite | 75 executed: 74 passed, 1 optional NetworkX skip | No test failures; no claim of NetworkX topology coverage |
| Default harness | 10/10 `run-all`, 10/10 `verify-all` | Existing implemented experiments and fresh receipt checks passed |
| Optimized `-O` | Same challenge observations as normal execution | Correctness checks were not disabled by optimization |
| No-op `os.replace` mutant | Exit 1; `RuntimeError: atomic replacement failed` | A forged success from disabled replacement was rejected |
| Filesystem baseline | Injected in-place write failure left 0 bytes | Truncation on early failure was reproduced |
| Atomic replacement | Original preserved before rename; replacement installed on success | Correct for the bounded same-filesystem fixture |
| Naive lock | 2 synchronized claimants reported ownership | Check-then-create was not a mutual exclusion primitive |
| Sidecar `flock` | Second lock denied, then acquired after first release | Correct for local cooperating descriptors |
| Stream read / framing | `recv(4)` returned 2; two frames decoded; oversized and truncated frame rejected | Correct for the bounded socketpair fixture |

The report also records the operator's preservation and byte-for-byte restoration of prior ignored harness receipts and a final clean tracked worktree.

## Execution boundaries and nonclaims

The original managed execution sandbox initially denied DNS for Git operations and a local socket send. Identical authorized retries succeeded. These are recorded as **environment access restrictions**, not application defects; the report retains their failed attempt codes.

`NOT_TESTED`: power-loss and kernel-crash durability, filesystem/network locking across hosts, ACL/metadata preservation, post-rename failure, hostile writers, real TCP congestion, TLS, authentication, slow-client deadlines, throughput, production exploitability or vulnerability severity. The three examples remain **synthetic failure-class demonstrations**, not named critical product vulnerabilities.

The original file and its timestamp are preserved; this documentation PR does not rewrite the report's source revision or claim a second workstation execution. No publishing automation, network integration, dependencies or Pages deployment are added.

## Recheck

From the repository root:

```sh
sha256sum evidence/RETRO-GAUNTLET-001/RETRO-001-LOCAL-UV-REPORT.json
git show 5e3825f93885579f086f8d3650f07cd64b530632:challenges/RETRO-GAUNTLET-001/run.py | sha256sum
git show 5e3825f93885579f086f8d3650f07cd64b530632:tests/test_retro_gauntlet.py | sha256sum
git show 5e3825f93885579f086f8d3650f07cd64b530632:challenges/RETRO-GAUNTLET-001/README.md | sha256sum
```

Expected source SHA-256 values are contained in the report; verify **these historical blobs**, not the latest potentially edited working-tree files.
