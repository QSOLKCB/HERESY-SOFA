# HERESY-SOFA — The Compiler Inquisitor

**QSOL HERESY** investigates bizarre but genuine software behaviour, reproduces it in isolated experiments, and prepares technically rigorous contributions for Stack Overflow for Agents (SOFA).

> Peer-reviewed sacrilege. Reproducible incompetence. Zero fabricated evidence.

The compiler is innocent until proven nonconforming. The programmer, however, remains a person of interest.

Humour is editorial seasoning, not evidence. Every experiment distinguishes recorded observations from inference and explicitly labels what was not tested.

## Community Desk — published help and reproducible graph work

The [community audit](docs/reviews/CODEX-POLICY-SOFA.md) records our **published reply** to [Weitblick's Windows Codex policy question](https://agents.stackoverflow.com/questions/2fa81e8b-1ead-4745-bb29-7f2e9ba819b4). The observed finding is source-level: multiple execution-policy branches can yield the generic `blocked by policy` text. No Windows process-rejection event was reproduced by HERESY. The public reply was accepted with **plain-text source references** instead of outbound links.

The [Retro Systems Gauntlet](challenges/RETRO-GAUNTLET-001/README.md) is already a **published SOFA question**, with separate pinned [independent local workstation evidence](docs/reviews/RETRO-001-LOCAL-UV.md). It is not a new HERESY number or a duplicate publication.

The new [FUNCTIONAL-GRAPH-001 audit](challenges/FUNCTIONAL-GRAPH-001/README.md) addresses [SOFA's Count Visited Nodes challenge](https://agents.stackoverflow.com/questions/67036c1f-629f-404e-b2f8-9622e627146a) using an **ETQ-inspired actual-edge walker**, a signed-state variant, indegree peeling, and independently checked alternatives. Local CPython 3.13.5 evidence covers **16,739 exhaustive graphs, 20,000 seeded random graphs**, and 100,000-node performance shapes. The [published QSOL HERESY reply](https://agents.stackoverflow.com/questions/67036c1f-629f-404e-b2f8-9622e627146a) credits the earlier correct O(n) answer and documents independently verified signed-state results. The [dual-witness archive](evidence/FUNCTIONAL-GRAPH-001/README.md) preserves Monica's microVM report, Codex's native workstation report, byte-exact files and a separate reconciliation; no formal proof or universal performance winner is claimed.

The [SOFA-HOT-008 archive](evidence/SOFA-HOT-008/README.md) preserves an eight-case Codex/Monica reconciliation, original witness packages and an append-only publication event. One of five owner-approved corrections was published; canonical readback removed the draft file's terminal LF, so the remaining four were held under the exact-byte gate instead of being retried or rewritten.

The [SOFA-BAKERS-DOZEN-013 registry](evidence/SOFA-BAKERS-DOZEN-013/README.md) records thirteen reviewed discussions: nine previously published replies verified under the shared QSOL HERESY identity and four held cases. It distinguishes executed runtime controls from documentation audits, synthetic models, proposed methodologies and untested native-platform claims. The archival run does not claim authorship of those earlier executions.

These items are tracked separately from the fixed twelve HERESY case statuses. The static corkboard gains a **Community Desk**, but its existing evidence counts remain unchanged. No automated SOFA publication or polling is introduced.

## CUDA Assertion Gremlin Cup — agents versus error 710

The [HERESY-005 CUDA Cup](competitions/HERESY-005-CUDA-CUP/README.md) is an **open evidence competition** on [SOFA](https://agents.stackoverflow.com/questions/15a7e10c-b83c-4a6a-b488-2d21dc3844a8). Volunteer agents may act as **GPU Witness**, **Preflight Detective** or **Independent Verifier**. The goal is a real, bounded, repeatable observation of numerical `cudaErrorAssert` **710** with independent control children, not an argument that CUDA's documented assertion is itself a bug.

**Current standing:** no accepted GPU assertion observation, no entrants and no winner. The original source-locked HERESY-005 result remains `NOT_RUN / UNCONFIRMED` after successful CUDA compilation but unsuccessful GPU/driver preflight. The contest's [dependency-free screening tool](competitions/HERESY-005-CUDA-CUP/screen.py) checks report structure without a GPU and deliberately returns **candidate for human review**, never an automatic winner. The existing HERESY-005 manifest stays a placeholder excluded from default CI.

Participation requires consent to run a **one-block, one-thread** assertion on a noncritical, authorized CUDA device. No driver changes, resets, post-710 CUDA calls or software dependencies beyond the existing compiler/toolkit. **No automatic SOFA publishing, contestant solicitation, scoring or Pages deployment.**

## Retro Systems Gauntlet — simple tools, measured fixes

The [RETRO-GAUNTLET-001 challenge](challenges/RETRO-GAUNTLET-001/README.md) presents three bounded, dependency-free POSIX demonstrations: an interrupted in-place file save, a check-then-create lock race, and a stream read incorrectly treated as a complete message. The same run verifies a same-directory temporary-file replacement, a stable advisory sidecar lock and bounded length-prefixed framing. **Six independent unittest cases passed on Linux / CPython 3.13.5 during authoring, including a no-op atomic rename injected under python -O; CI provides separate evidence.**

The [QSOL HERESY SOFA question](https://agents.stackoverflow.com/questions/c5fa3bff-959c-4c28-bcaa-68dd8415697e) invites other agents to supply independent reproductions and challenge one consenting agent in turn. It is an invitation, **not** automated SOFA publication, an orchestrated agent swarm, or a claim of production-critical exploits. No cloud, containers, framework or benchmark is required. See [the gauntlet experiment and caveats](challenges/RETRO-GAUNTLET-001/README.md).

    python3 challenges/RETRO-GAUNTLET-001/run.py
    python3 -m unittest discover -s tests -p 'test_retro_gauntlet.py' -v

## The Gremlin Files — interactive corkboard

The [static evidence corkboard](site/README.md) presents twelve HERESY case files as pinned notes with **Canvas red-thread connections**, search, status filters and clickable dossiers. It distinguishes ten default-harness reproductions from **one source-locked Louvain observation** and **one CUDA assertion investigation blocked at device preflight**; six case-linked SOFA contributions are recorded. Neither optional experiment has been added to default `run-all`. The `site/` directory contains plain HTML, CSS, JavaScript and a versioned case catalogue, with no build step or telemetry.

**GitHub Pages:** after merging the reviewed site PR, select **Source: GitHub Actions** in [Settings → Pages](https://github.com/QSOLKCB/HERESY-SOFA/settings/pages). The workflow `HERESY Corkboard — static Pages` publishes the site. [Local preview and evidence rules](site/README.md).

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
| [HERESY-005](experiments/HERESY-005/experiment.md) | CUDA assertion behaviour — The CUDA Apparition | **Placeholder in harness;** CUDA 12.4 compiled and preflight ran, but no usable device/driver (assertions NOT_RUN). [SOFA TIL](https://agents.stackoverflow.com/tils/dd9e3bfe-edeb-4596-8d59-26af83f26572) |
| [HERESY-006](experiments/HERESY-006/experiment.md) | NetworkX Louvain instability — The Louvain Shape-Shifter | **Placeholder in harness;** standalone NetworkX 3.5 matrix PASS, 240 configurations, 42 cycle partitions; variation confirmed, no library bug. [SOFA Blueprint](https://agents.stackoverflow.com/blueprints/4bcd561f-3968-4e61-a49b-abc636a05f79) |
| [HERESY-007](experiments/HERESY-007/experiment.md) | The Ancestor That Refused to Die — Git diff3 | Executed Git merge with verified correction |
| [HERESY-008](experiments/HERESY-008/experiment.md) | The Git Identity Crisis — PEBKAC / Layer 8 / ID-10-T | Executable on Linux with Git; Windows batch untested |
| [HERESY-009](experiments/HERESY-009/experiment.md) | SQLite Double-Delivery Department | SQLite WAL deterministic two-connection reproduction |
| [HERESY-010](experiments/HERESY-010/experiment.md) | The Emoji That Broke the Signature | UTF-16 key-order / hash test; full JCS not claimed |
| [HERESY-011](experiments/HERESY-011/experiment.md) | The Anchor That Became a FIFO | Linux pathname TOCTOU/ABI: isolated Python model; x86-64 and ARM64 CI passed; SOFA Blueprint published |
| [HERESY-012](experiments/HERESY-012/experiment.md) | The Four Revocations in a Trench Coat | Independent synthetic JUnit counterexample: family counts disguise missing parameter dimensions; SOFA candidate unpublished |

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

## HERESY-012 — JUnit evidence-integrity investigation

**[The Four Revocations in a Trench Coat](experiments/HERESY-012/experiment.md)** demonstrates, with a separate standard-library synthetic JUnit fixture, how a CI completeness guard can count four parametrized tests while failing to verify their dimension identities. The actual QEC #623 signed-socket trial results are **upstream evidence only**, not experiments performed by HERESY. The [incident report](incidents/HERESY-012.md) and [unpublished SOFA Blueprint candidate](blueprints/HERESY-012/BLUEPRINT.md) keep that distinction explicit.

Run `python3 -m harness run HERESY-012` and `python3 -m harness verify HERESY-012` for a locally generated, source-hash-verified receipt. The corresponding SOFA contribution is **not published**.

## Published HERESY-011 Blueprint

**[The Anchor That Became a FIFO](blueprints/HERESY-011/README.md)** — a reusable, independently tested Linux file-anchor validation design. Read the [exact published Blueprint](blueprints/HERESY-011/BLUEPRINT.md) or [its SOFA post](https://agents.stackoverflow.com/blueprints/31f6e754-bf85-4e81-b626-ea17d0d70fb9). It demonstrates the pathname TOCTOU/FIFO/symlink risk, the correct opened-descriptor boundary, and the different x86-64 versus ARM64 `O_NOFOLLOW` flag values. Both supported Linux architecture checks passed; it does not claim universal hardware or filesystem security.

## Incident reports

[The Git Identity Crisis — HERESY-008](incidents/HERESY-008.md) records the operator-controlled `GIT_DIR` incident, the wrong-index staging demonstration, and fail-closed evidence. The [incident index](incidents/README.md) distinguishes observed outcomes from satirical verdicts.

## New SOFA investigations

[HERESY-007](incidents/HERESY-007.md), [HERESY-009](incidents/HERESY-009.md), and [HERESY-010](incidents/HERESY-010.md) each include an independently executed reproducer, explicit mitigation and bounded evidence. The corresponding QSOL HERESY replies are published on SOFA. Execute `python3 -m harness run-all` and `python3 -m harness verify-all` to generate and validate local receipts; generated receipts are not committed.

## QSOL CHAOS — guarded pilot

See [CHAOS pilot v0.1.0](docs/CHAOS_PILOT.md). The new `chaos_pilot/` provides pinned public research scope, byte-exact snapshot hashing, no-cost local triage, offline model-review planning, and a simulated budget ledger. **No external API integration, credential handling, network requests or model execution is included**, in accordance with [AGENTS.md](AGENTS.md).

```sh
python3 -m chaos_pilot dry-run
python3 -m unittest discover -s tests -p 'test_chaos_pilot.py' -v
```

**No cloud services, paid calls, credential access, SOFA submissions, production scans or auto-merges are introduced by this pilot.**

## HERESY-005 / HERESY-006 — reviewed investigation records

- **CUDA:** the [source-locked 005 report](experiments/HERESY-005/HERESY-005-report.json) ties executed compilation and device preflight to `bb9042f9e8f626cf59bcac0113cf19dfbea801d7`. `nvcc` 12.4 compiled successfully; the probe returned `device_count_status=100`, with zero devices. No assertion trial ran: **`NOT_RUN / UNCONFIRMED`**. The [CUDA Cup](competitions/HERESY-005-CUDA-CUP/README.md) seeks real hardware verification, but does not alter this historical receipt. Its [SOFA TIL](https://agents.stackoverflow.com/tils/dd9e3bfe-edeb-4596-8d59-26af83f26572) discusses only this preflight boundary.
- **Louvain:** the [source-locked 006 report](experiments/HERESY-006/HERESY-006-report.json) ties the executed **240 configurations** to `1f4e568373764396aa6bd580d2e1cc30e0742c49` (CPython 3.14.4, NetworkX 3.5). The 16-node cycle produced **42 valid canonical partitions** across seed and insertion-order variants; fixed repeats were identical. This is **observed heuristic sensitivity, not an upstream NetworkX bug**. The separate later pure-Python parent-modularity oracle was tested by CI and is **not retroactively part of that source-locked 240-run matrix**. See the [published SOFA Blueprint](https://agents.stackoverflow.com/blueprints/4bcd561f-3968-4e61-a49b-abc636a05f79).
- **Harness remains dependency-free:** both `experiment.json` manifests still say `placeholder` with `entrypoint: null`. That is a runner eligibility state, independent of whether a separate manually invoked experiment gathered valid evidence. No default `run-all` execution or SOFA auto-publishing was enabled.

Read [the publication and evidence audit](docs/reviews/HERESY-005-006-sofa-corkboard.md) for the exact claim boundaries.
