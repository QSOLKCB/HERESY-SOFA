# HERESY-SOFA — The Compiler Inquisitor

**QSOL HERESY** investigates bizarre but genuine software behaviour, reproduces it in isolated experiments, and prepares technically rigorous contributions for Stack Overflow for Agents (SOFA).

> Peer-reviewed sacrilege. Reproducible incompetence. Zero fabricated evidence.

The compiler is innocent until proven nonconforming. The programmer, however, remains a person of interest.

Humour is editorial seasoning, not evidence. Every experiment distinguishes recorded observations from inference and explicitly labels what was not tested.

## Quick start

Requires Python 3. No third-party packages are needed.

```sh
python3 -m harness list
python3 -m harness run HERESY-001
python3 -m harness verify HERESY-001
python3 -m harness run-all
```

Receipts are written to `receipts/generated/` and are intentionally not committed. Each receipt records the command, exit code, runtime versions, observations, timestamp, and SHA-256 hashes of its evidence inputs.

## Experiment catalogue

| ID | Subject | State |
|---|---|---|
| HERESY-001 | Python JSON Infinity Smuggling | Executable on Linux |
| HERESY-002 | The stdin Custody Battle | Executable on Linux with Bash |
| HERESY-003 | Schrödinger's SQLite Backup | Executable on Linux |
| HERESY-004 | Windows Batch File Line-Ending Tribunal | Linux byte-level reproduction; `cmd.exe` not tested |
| HERESY-005 | CUDA assertion behaviour | Placeholder; not tested |
| HERESY-006 | NetworkX Louvain instability | Placeholder; not tested |
| HERESY-007 | Git conflict-marker pathology | Placeholder; not tested |
| [HERESY-008](experiments/HERESY-008/experiment.md) | The Git Identity Crisis — PEBKAC / Layer 8 / ID-10-T | Executable on Linux with Git; Windows batch untested |

Use `python3 -m harness verify-all` to validate all generated receipts and their evidence hashes. `python3 -m unittest discover -s tests -v` runs the regression suite.

## Evidence and SOFA

An experiment's `experiment.md` records its hypothesis, environment, minimal reproduction, expected behaviour, actual observations, mitigation, limitations, and provenance. Results only become claims after execution; unavailable platforms are never simulated or described as tested.

SOFA publication is disabled by default. `sofa/manifest.json` records the original published TIL and supplies metadata fields for future question, TIL, Blueprint, Playbook, and reply links. Local evidence, drafts, and published contributions remain distinct. Nothing in this repository publishes content, contacts SOFA, or stores credentials.

See [CONTRIBUTING.md](CONTRIBUTING.md), [the invariants](docs/INVARIANTS.md), [methodology](docs/METHODOLOGY.md), [SOFA policy](docs/SOFA_POLICY.md), and [roadmap](docs/ROADMAP.md).

## Stage 2 — Evidence Quality and Blueprint candidates

The [JSON finite-number Blueprint v0.2.0](blueprints/JSON-FINITE-NUMBERS-v0.2.0/README.md) includes a **separate Python standard-library HTTP implementation** and 15 regression tests for parser overflow, nonstandard constants, duplicate keys, integer limits, and strict JSON serialization. It is an **unpublished** SOFA candidate, not a production deployment or a confirmed vulnerability.

```sh
python3 -m unittest discover -s blueprints/JSON-FINITE-NUMBERS-v0.2.0 -p 'test_*.py' -v
```

See the [evidence review checklist](docs/EVIDENCE_REVIEW.md) before promoting any new experiment or Blueprint. This repository does not require Node.js and does not publish to SOFA.

## Incident reports

[The Git Identity Crisis — HERESY-008](incidents/HERESY-008.md) records the operator-controlled `GIT_DIR` incident, the wrong-index staging demonstration, and fail-closed evidence. The [incident index](incidents/README.md) distinguishes observed outcomes from satirical verdicts.
