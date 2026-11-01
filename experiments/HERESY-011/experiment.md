# HERESY-011 — The Anchor That Became a FIFO

**Scope:** deterministic Linux TOCTOU reproduction and architecture-specific ABI control. No production anchors, external targets, or SOFA publication.

## Origin and hypothesis

[QSOLKCB/TOMBSTONE PR #22](https://github.com/QSOLKCB/TOMBSTONE/pull/22), reviewed at source head 339a57d3b19dc0e6d223ac3e1e033a66a2feeb4e, exposed a gap between a path-level symlink_metadata check and File::open. A concurrent renameat2(RENAME_EXCHANGE) could substitute a FIFO (blocking the open) or a symlink (redirecting the trusted head). The initial correction mistakenly reused x86-64 O_NOFOLLOW on ARM64; ARM64 CI rejected it, and the later corrected version checks an opened descriptor.

The upstream [eight-configuration Phase 16 CI run](https://github.com/QSOLKCB/TOMBSTONE/actions/runs/41331092253) is **external, reported evidence**, not HERESY-SOFA's execution of the TOMBSTONE Rust binary.

## Reproduction

Run the repository harness: python3 -m harness run HERESY-011; then python3 -m harness verify HERESY-011. The Python standard-library reproducer creates a disposable normal 64-lowercase-hex anchor, FIFO and symlink to a deliberately wrong head. It uses Linux renameat2(RENAME_EXCHANGE) and a child handshake to **force** the swap between the unsafe path check and open. Every child has a timeout, and a blocked child is killed and reaped.

Expected: the unsafe FIFO case blocks until killed; the unsafe symlink case reads the wrong head; the corrected open rejects both without blocking and accepts the regular-file control. The corrected comparison uses os.O_NONBLOCK, os.O_NOFOLLOW, os.fstat and a bounded same-descriptor read.

Native os.O_NOFOLLOW is checked against the supported Linux target ABI. **Only on ARM64**, the deliberately wrong x86-64 numeric constant is tested for symlink following. An x86-64 execution does not establish ARM64 behaviour.

## Published reference

The complete reviewed [SOFA Blueprint](../../blueprints/HERESY-011/BLUEPRINT.md) is archived locally with [evidence and publication metadata](../../blueprints/HERESY-011/README.md). The [SOFA publication](https://agents.stackoverflow.com/blueprints/31f6e754-bf85-4e81-b626-ea17d0d70fb9) is separately identified in the manifest.

## Limits and acceptance

The deterministic interleaving proves a race is possible; it does not measure probability or execute the original TOMBSTONE CLI. No claims for other Linux platforms, Windows, malicious kernels, real hardware, filesystem deletion, signer identity, chronology, or independent custody. An anchor file alone does not authenticate its source.

The x86-64 and ARM64 checks passed in HERESY-SOFA run `41332181292`, and repository evidence checks passed in run `41332181270`. Codex reported no actionable issues at reviewed commit `bbc666ff26fb66552c069d49e22308cc30242a46`. **SOFA Blueprint published** under ID `31f6e754-bf85-4e81-b626-ea17d0d70fb9` (reviewed, human-requested publication; no automatic publishing enabled).

> The pathname supplied an alibi. The descriptor testified under oath. The hardcoded flag attempted to flee to another architecture.
