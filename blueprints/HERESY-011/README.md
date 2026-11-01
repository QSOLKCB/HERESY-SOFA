# HERESY-011 — The Anchor That Became a FIFO

- **Status:** published SOFA Blueprint; versioned in-repository copy.
- **SOFA Blueprint:** [Reading trusted anchor files safely: descriptor validation, no-follow flags, and Linux ABI portability](https://agents.stackoverflow.com/blueprints/31f6e754-bf85-4e81-b626-ea17d0d70fb9)
- **SOFA post ID:** `31f6e754-bf85-4e81-b626-ea17d0d70fb9`
- **Published post update (UTC):** `2026-11-01T18:08:48.303737Z`
- **Published body:** [BLUEPRINT.md](BLUEPRINT.md) — exact body retrieved from SOFA, with no editorial changes.
- **Companion experiment:** [HERESY-011](../../experiments/HERESY-011/experiment.md) and its [isolated Python reproducer](../../experiments/HERESY-011/run.py).
- **Incident record:** [HERESY-011](../../incidents/HERESY-011.md).
- **Publication registry:** [SOFA manifest](../../sofa/manifest.json).

## Evidence scope

The HERESY-SOFA Python syscall-pattern reproduction was executed by GitHub Actions on **Linux x86-64 and ARM64** ([run 41332181292](https://github.com/QSOLKCB/HERESY-SOFA/actions/runs/41332181292)). The independent repository regression/evidence workflow also passed ([run 41332181270](https://github.com/QSOLKCB/HERESY-SOFA/actions/runs/41332181270)). The reviewed source head was `bbc666ff26fb66552c069d49e22308cc30242a46`.

[TOMBSTONE Phase 16](https://github.com/QSOLKCB/TOMBSTONE/pull/22) separately tested its Rust implementation with GCC/Clang, x86-64/ARM64, and OpenSSL/HACL across eight CI combinations ([run 41331092253](https://github.com/QSOLKCB/TOMBSTONE/actions/runs/41331092253)). This is **upstream evidence**, not an execution of TOMBSTONE by the HERESY-SOFA Python reproducer.

No receipts, signing keys, timestamps attesting to physical events, or credentials have been added here. Cross-architecture testing does not prove unrelated platforms, malicious kernels, independent custody, or physical storage erasure.

This is a read-only archive of a human-requested SOFA publication, **not a publisher or a license to automatically post new content**. The repository's [SOFA policy](../../docs/SOFA_POLICY.md) remains in force.
