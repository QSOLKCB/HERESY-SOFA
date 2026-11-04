# HERESY-006 — The Louvain Shape-Shifter

**Status: placeholder; evidence review pending.** The independently executable runner does not make NetworkX a repository dependency, and the harness manifest intentionally remains `placeholder` with no entrypoint.

## Falsifiable hypothesis

NetworkX Louvain may return different valid partitions for the same labelled, weighted topology under different random seeds or graph insertion orders. Such a result is compatible with heuristic optimization and is not automatically a NetworkX defect. No divergence leaves the hypothesis unconfirmed; it is not grounds to invent instability.

## Deterministic fixtures and matrix

- Stability control: three five-node cliques joined by weight-0.05 edges.
- Symmetric case: an unweighted 16-node cycle.
- Tie-prone case: four identical triangles and two symmetric bridge nodes with equal-weight choices.

The parent executes isolated workers for seeds 0–63, three identical fixed-seed executions, natural/reversed/interleaved node and edge insertion orders at seeds 0, 17 and 63, and process hash seeds 0, 1, 7 and 42. Topology fingerprints prove that insertion order does not alter labels, weights, or edges. Partitions are canonicalized by sorted node membership, never by NetworkX's returned list order.

Every recorded partition must cover every graph node exactly once. Its modularity and recomputed modularity must both be finite, then agree within `1e-12`. A missing dependency, nonzero child, timeout, malformed output, incomplete seed/fixture set, coverage error, or modularity mismatch makes the run `NOT_RUN` or `FAIL`, never green paperwork.

Failed worker records retain **bounded, sanitized** stderr and an allowlisted structural observation (including canonical partition members and the reported modularity), with explicit truncation when necessary. Arbitrary worker keys, local paths, credentials and raw diagnostic streams are not published. A broken fixed-seed repeat or failed separated-clique control now forces top-level `FAIL` and a nonzero exit, even if every individual worker record is structurally valid.

`PYTHONHASHSEED` is fixed when each worker interpreter starts. The parent controls that environment value and rejects a mismatched worker report; this proves the requested process configuration was launched and echoed, not that Louvain causally used the hash seed internally.

## Temporary dependency and command

Use an operator-approved disposable environment; do not add NetworkX to the project's mandatory dependencies:

```sh
python3 -m venv /tmp/heresy006-venv
/tmp/heresy006-venv/bin/python -m pip install --no-deps 'networkx==3.5'
/tmp/heresy006-venv/bin/python experiments/HERESY-006/run.py \
  --output experiments/HERESY-006/HERESY-006-report.json
```

The result is `CONFIRMED` only if at least one partition changes across random seeds or controlled construction order while all integrity checks pass. Fixed-seed reproducibility, hash-seed effects, insertion-order effects, seed effects, and contract violations are reported separately. A fixed-seed observation does not establish behavior for every platform or NetworkX version.

## Reproduction and verification

The sanitized report preserves every tested configuration, exact commands and child exits, versions, expected versus actual outcomes, source revision, source SHA-256 hashes, limitations, and explicit claim classifications. Re-run it from a clean checkout of the recorded commit and verify:

```sh
sha256sum experiments/HERESY-006/{experiment.json,experiment.md,run.py}
/tmp/heresy006-venv/bin/python -m unittest tests.test_heresy006 -v
```

The report is not a harness receipt or a SOFA publication. Raw `receipts/generated/` output remains local and uncommitted.

**Historical evidence boundary:** The committed 240-configuration `HERESY-006-report.json` records the executed source at `1f4e568373764396aa6bd580d2e1cc30e0742c49`. Later fail-closed diagnostic changes do not retroactively re-run that matrix or change its original evidence hashes. Re-run the current code in an approved NetworkX environment to create a new report bound to the new source revision; keep the earlier report's provenance unchanged.
