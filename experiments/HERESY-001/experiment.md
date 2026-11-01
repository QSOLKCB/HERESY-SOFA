# HERESY-001 — Python JSON Infinity Smuggling

- **Hypothesis:** Python's JSON decoder converts the valid JSON numeric token `1e999` to positive infinity through `parse_float`, so `parse_constant` alone does not reject the overflow.
- **Environment:** Python 3 standard library; run on Linux via `python3 -m harness run HERESY-001`.
- **Minimal reproduction:** `json.loads("1e999", parse_constant=reject)` and observe that it returns infinity without calling `reject`.
- **Expected behaviour:** Applications requiring finite numbers reject overflow during `parse_float`; strict serializers refuse non-finite floats.
- **Actual observations:** The runner records whether the parsed value is infinite, whether `parse_constant` ran, whether a finite-checking parser rejected the value, whether `Decimal` retained a finite value, and whether strict serialization rejected infinity. This section describes the experiment's observed fields, not a result from an unexecuted platform.
- **Mitigation:** Supply `parse_float` that checks `math.isfinite(float(token))` and raises on overflow; alternatively use `parse_float=Decimal` when arbitrary decimal magnitude is appropriate. Serialize with `allow_nan=False`.
- **Limitations:** A finite `float` can still lose precision; `Decimal` has different arithmetic and serialization requirements. This reproduction does not validate application-specific numeric ranges.
- **Evidence provenance:** `run.py` is the executable fixture. The harness receipt hashes the manifest and entrypoint and records the actual runtime and output.
