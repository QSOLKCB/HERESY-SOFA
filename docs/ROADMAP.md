# Roadmap

## Stage 1 — Foundation

- [x] Standard-library experiment harness and machine-readable receipts
- [x] Initial JSON, stdin, SQLite WAL, and line-ending reproductions
- [x] Regression coverage, evidence policy, and SOFA metadata

## Stage 2 — Evidence quality

- [ ] Review reproducibility across supported Python and SQLite versions (current tests cover the CI runner and the preserved local environment only).
- [x] Add an independently implemented JSON finite-number HTTP reference and tests; independent external/production review remains open.
- [x] Establish an [evidence review checklist](EVIDENCE_REVIEW.md) without weakening the claim vocabulary.
- [x] Preserve [JSON finite-number Blueprint candidate v0.2.0](../blueprints/JSON-FINITE-NUMBERS-v0.2.0/README.md) as **unpublished**, with no automatic SOFA writes.

## Stage 3 — New candidates

- [x] Promote Git conflict-marker placeholder (HERESY-007) with an executed disposable Git merge, bounded parser mitigation and tests.
- [ ] Promote CUDA assertion and NetworkX Louvain placeholders only after safe fixtures and a tested mitigation exist.
- [x] **HERESY-011 candidate — The Anchor That Became a FIFO (Linux TOCTOU):** investigate the TOMBSTONE CLI `apps/cli/src/main.rs` path-check/open race in `verify-chain --trusted-head-file`. **Source status:** Codex review reports a Linux `renameat2(RENAME_EXCHANGE)` reproduction in which a regular 64-hex anchor can be exchanged with a FIFO between `symlink_metadata` and `File::open`, causing an indefinite `wait_for_partner` block; symlink substitution may also bypass the pathname check. **HERESY-SOFA status:** independent Linux x86-64 Python-model reproduction executed locally; ARM64 requires its separate CI job; not published or claimed to be direct TOMBSTONE Rust execution. See [the HERESY-011 experiment](../experiments/HERESY-011/experiment.md).
  - Build an isolated, bounded Linux-only reproducer using a disposable temporary directory, an ordinary anchor, a FIFO, and a symlink; enforce a subprocess timeout/cleanup so the regression never hangs CI. No live trusted-head or production paths.
  - Compare unsafe path-level `symlink_metadata` + `File::open` against a fixed approach: open with no-follow/nonblocking protections, validate **the opened descriptor** is regular via `fstat`/`File::metadata`, then perform the bounded read from that same descriptor. Document exact platform/flag limitations; do not claim Windows equivalence without execution.
  - Positive controls: valid regular 64-hex anchor accepted; negative controls: FIFO and symlink fail promptly, repeated concurrent rename-exchange never blocks or follows a substituted link, invalid/nonregular descriptor returns a deterministic error. Record actual exit codes, timeouts, descriptor type, toolchain and source commit as evidence rather than claiming a successful race from inference.
  - [x] Implement isolated deterministic Linux Python reproduction and bounded subprocess timeouts (no production targets). [ ] Require both supported architectures' actual CI and review before promoting to a Blueprint or SOFA contribution. **No auto-publishing.**
- [x] Add SQLite WAL queue double-drain (HERESY-009) and UTF-16/JCS key-ordering (HERESY-010) experiments with bounded evidence and SOFA replies.
- Add Windows execution evidence before making claims about `cmd.exe`.

- [x] Add HERESY-008 PEBKAC/Layer-8 incident as a separate executable Git experiment with negative-control receipt tests; keep the existing CUDA, NetworkX and conflict-marker placeholders unchanged.

## Stage 4 — SOFA contributions

- Prepare reviewed drafts and link them to local experiments.
- Consider authenticated SOFA MCP integration only when explicitly requested and reviewed; never enable autonomous publishing.
