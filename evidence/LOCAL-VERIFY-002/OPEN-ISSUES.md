# LOCAL-VERIFY-002 — open issues

## Mypy 2.3.1

- **Status:** `NOT_TESTED`.
- **Blocker:** `uvx --offline --from mypy==2.3.1 mypy --version` reported that the exact package was absent from cache.
- **Prerequisite:** owner-authorized isolated acquisition from the official package registry, followed by hash capture and a separately recorded offline execution.
- **Required evidence:** rerun every default/strict fixture twice, capture diagnostic codes/locations and compare bare versus annotated dataclass instances.
- **Negative controls:** GA05, GA06, DC02, DC03 and NC01.

## Pyright 1.1.414

- **Status:** `NOT_TESTED`.
- **Blocker:** no verified Pyright executable or cache artifact. Existing Node 22.18.0 is not itself Pyright.
- **Prerequisite:** an owner-approved, version-pinned Pyright 1.1.414 artifact and verified compatible Node runtime. Do not use implicit Python-wrapper Node/npm bootstrap.
- **Required evidence:** run every applicable fixture twice, in normal and strict configurations, preserving `reportInvalidTypeForm` and all other rule identifiers and source ranges.
- **Negative controls:** custom `__class_getitem__`, literal ellipsis in `Generic[*Ts]`, ordinary generic arity and runtime-only GenericAlias metadata.

## Cross-checker interpretation

- Mypy 1.19.1's `"GenericAlias" not callable [operator]` result needs comparison with the two unavailable checkers; CPython execution proves only that the object is callable at runtime.
- The existing SOFA reports of mypy 2.3.1 and Pyright 1.1.414 remain contributor evidence, not native execution by this campaign.
- No package download is authorized by this open-issues record.

## Phase boundary

LOCAL-VERIFY-003 and LOCAL-VERIFY-004 were not started. They require separate owner progression after review of this PR.
