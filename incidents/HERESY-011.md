# HERESY-011 — The Anchor That Became a FIFO

**Status:** isolated Python reproducer executed on Linux x86-64 and AArch64 via CI run `41332181292`, with verified receipts and clean reviewed PR #6. SOFA Blueprint published under ID `31f6e754-bf85-4e81-b626-ea17d0d70fb9`.

## What was reported

[QSOLKCB/TOMBSTONE PR #22](https://github.com/QSOLKCB/TOMBSTONE/pull/22) exposed a TOCTOU flaw between symlink_metadata(path) and File::open(path). A concurrent atomic pathname exchange could present a FIFO (which blocks open) or a symlink to a different trusted head. The initial nonblocking/no-follow fix used an x86-64 numeric O_NOFOLLOW flag on AArch64, where the ABI differs. TOMBSTONE's corrected source is at [339a57d](https://github.com/QSOLKCB/TOMBSTONE/commit/339a57d3b19dc0e6d223ac3e1e033a66a2feeb4e).

## What we independently test

[The isolated HERESY-011 fixture](../experiments/HERESY-011/run.py) forces an atomic swap in a disposable Linux directory, compares the unsafe pathname-check/open with target-correct open/fstat/same-FD read, and records real timeouts and outcomes. The experiment does **not** execute TOMBSTONE's Rust binary or reproduce production conditions. Generated receipts stay in the ignored receipts/generated directory; they are not committed as executed evidence.

## Published Blueprint

The [SOFA-published design and evidence boundaries](../blueprints/HERESY-011/README.md) include a [verbatim snapshot of the Blueprint body](../blueprints/HERESY-011/BLUEPRINT.md).

## Mitigation and limitations

Validate the opened descriptor, use O_NONBLOCK plus the target-appropriate O_NOFOLLOW, and read only that descriptor with a strict length limit. Neither a correctly formatted local anchor nor a green test establishes independent custody, physical history or hardware proof. Both x86-64 and ARM64 jobs executed on supported Linux CI runners; this does not establish other targets.

**SOFA:** Blueprint published after review under ID `31f6e754-bf85-4e81-b626-ea17d0d70fb9`. The compiler is innocent; the pathname is under investigation.
