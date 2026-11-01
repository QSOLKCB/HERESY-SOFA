# Contributing

Submit an engineering absurdity only when it is reproducible and useful after the jokes are removed.

## Adding an experiment

1. Create `experiments/HERESY-NNN/` with an `experiment.json`, executable `run.py`, and `experiment.md`.
2. State the hypothesis and environment. Separate expected behaviour from observations, and label claims `executed`, `inferred`, `not_tested`, or `unsupported`.
3. Use deterministic inputs, seeded randomness where needed, standard-library dependencies, and isolated temporary directories. Do not rely on a network or expose private environment data.
4. Describe the smallest reproduction, expected and actual results, a tested mitigation, limitations, and evidence provenance.
5. Add regression tests under `tests/`. Verify exit codes and failure paths rather than only testing the happy path.
6. Run `python3 -m unittest discover -s tests -v`, the experiment, and `python3 -m harness verify EXPERIMENT_ID`. Inspect and remove any generated receipt before submitting.
7. Update the catalogue or documentation only where relevant.

## Evidence and publication

Receipts are local execution evidence, not publication drafts. Draft material belongs in `sofa/drafts/`; published links and status belong in `sofa/manifest.json`. Publishing is disabled by default and always requires explicit human review and an authenticated, approved workflow outside this repository. Never include credentials or claim a publication that did not happen.

See [INVARIANTS](docs/INVARIANTS.md), [METHODOLOGY](docs/METHODOLOGY.md), and [SOFA_POLICY](docs/SOFA_POLICY.md) before proposing evidence or publication-related changes.
