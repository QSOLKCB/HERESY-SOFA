# JSON finite-number contract — Blueprint candidate v0.2.0

**State:** Unpublished SOFA Blueprint candidate; not deployed in production.

The independent Python standard-library reference uses an in-process HTTP listener bound only to `127.0.0.1` and an ephemeral port. It tests strict parsing/serialization, domain and JSON integer bounds, duplicate object keys, and resource-size limits. This reference is **not a hardened production server**.

## Run the reference test suite

```sh
python3 -m unittest discover -s blueprints/JSON-FINITE-NUMBERS-v0.2.0 -p 'test_*.py' -v
```

Or from this directory:

```sh
python3 -m unittest -v test_boundary
```

Requires Python 3 and loopback access; no third-party dependencies. Do **not** publish to SOFA automatically.

## Provenance

- Blueprint source: `BLUEPRINT_CANDIDATE.md` (version 0.2.0).
- Independent implementation and 15 test cases: `finite_json_boundary.py`, `test_boundary.py`.
- Prior local evidence was captured on CPython 3.13.5 and Node.js 22.16.0. This repository does not require Node.js; the cross-runtime result is a *historical observation* documented in the Blueprint, not a test run by this repository's CI.
- The original evidence archive, `QSOL-HERESY-JSON-Blueprint-v0.2.0.tar.gz`, remains preserved separately. Generated logs and receipts are **not** committed here as canonical outputs.

The tests do not establish the claimed behavior of every Python version, JavaScript engine, or production HTTP server. For acceptance, use [`docs/EVIDENCE_REVIEW.md`](../../docs/EVIDENCE_REVIEW.md).