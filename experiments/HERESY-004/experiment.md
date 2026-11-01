# HERESY-004 — Windows Batch File Line-Ending Tribunal

- **Hypothesis:** Blindly converting LF to CRLF can turn existing CRLF into CRCRLF; canonicalizing input first produces an idempotent byte-level normalizer.
- **Environment:** Linux, Python 3 standard library, fixed byte fixture.
- **Minimal reproduction:** Replace every LF byte with CRLF in a fixture that already includes CRLF and inspect hexadecimal bytes.
- **Expected behaviour:** Naive replacement contains CRCRLF; canonical normalization emits stable CRLF bytes and a second pass changes nothing.
- **Actual observations:** The executable records source, naive, and normalized bytes as hex, tests for duplicated carriage returns, and checks idempotence.
- **Mitigation:** Normalize CRLF and lone CR to LF before converting LF to the chosen output convention.
- **Limitations:** This proves byte transformations only. **Actual `cmd.exe` parsing and execution are `not_tested`** because this experiment runs on Linux; no Windows behaviour is inferred.
- **Evidence provenance:** A fixed in-memory byte string and SHA-256 are emitted as observations; no Windows results are generated.
