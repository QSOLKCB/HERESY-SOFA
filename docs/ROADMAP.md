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

- Promote CUDA assertion, NetworkX Louvain, and Git conflict-marker placeholders only after a minimal reproduction, safe fixtures, and a tested mitigation exist.
- Add Windows execution evidence before making claims about `cmd.exe`.

- [x] Add HERESY-008 PEBKAC/Layer-8 incident as a separate executable Git experiment with negative-control receipt tests; keep the existing CUDA, NetworkX and conflict-marker placeholders unchanged.

## Stage 4 — SOFA contributions

- Prepare reviewed drafts and link them to local experiments.
- Consider authenticated SOFA MCP integration only when explicitly requested and reviewed; never enable autonomous publishing.
