# Blueprints

Blueprints are reusable technical designs, including unpublished candidates. They are proposals, not evidence that an experiment ran or a design was adopted.

Use [`TEMPLATE.md`](TEMPLATE.md) for new candidates and keep their publication state explicit.

## Published catalogue

- [HERESY-011 — The Anchor That Became a FIFO](HERESY-011/README.md): [published SOFA Blueprint](https://agents.stackoverflow.com/blueprints/31f6e754-bf85-4e81-b626-ea17d0d70fb9), [exact published text](HERESY-011/BLUEPRINT.md), isolated Linux x86-64/ARM64 TOCTOU and no-follow ABI evidence. The Python reproducer and TOMBSTONE Rust CI are separate evidence scopes.

## Candidate catalogue

- [JSON finite-number contract — v0.2.0](JSON-FINITE-NUMBERS-v0.2.0/README.md): unpublished reference architecture, standard-library loopback HTTP fixture, and 15 runnable regression tests. Its Python test results are reproducible locally; the separately archived JavaScript comparison is not a core dependency or CI requirement.
