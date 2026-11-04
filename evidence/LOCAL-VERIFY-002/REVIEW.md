# LOCAL-VERIFY-002 — version-pinned static-checker matrix

**Campaign state:** executed locally from repository commit `ddccc1214b7a5d5942c6755ffa4da2c144d0f6ad`; no dependency download, npm invocation, SOFA mutation or Phase B/C work.

**Executed scope:** Ubuntu 26.04.1 LTS, Linux 7.0.0-42-generic, x86_64; CPython 3.11.15, 3.12.13, 3.13.14 and 3.14.4; mypy 1.19.1 (`1.19.1-5build1`). The 14 fixtures produced 28 canonical checker rows and 56 runtime rows. Every executed row was repeated in a fresh process. All 195 harness checks and 11 negative controls passed.

## Priority findings

1. **The posted GenericAlias reply fails on all four CPython versions.** `GenericAlias[tuple[int, ...]]` raises `TypeError: type 'types.GenericAlias' is not subscriptable`; the proposed class declaration is never reached. The verbatim fixture SHA-256 is `cd557e23528bb459525391171c07cce3fddcb771d2fb8613e5c121ed1e87efe5`.

2. **The actual runtime constructor is not a static-typing repair.** `types.GenericAlias(tuple, (int, Ellipsis))` produces `tuple[int, ...]` metadata and accepts `(1, "unchecked")` on every executed interpreter. Mypy 1.19.1 nevertheless reports `"GenericAlias" not callable [operator]` for the runtime-valid call. Runtime metadata, value enforcement and checker support are three separate claims.

3. **Literal ellipsis is accepted by CPython's TypeVarTuple runtime machinery.** `Packed[int, ...]` and `Packed[...]` execute on CPython 3.11.15 through 3.14.4. Mypy 1.19.1 rejects both with `Unexpected "..." [misc]`. This disproves a universal Python runtime prohibition; it does not establish Pyright compatibility.

4. **Custom subscription interception is runtime-only in the executed scope.** The custom `__class_getitem__` fixture constructs `Foo[int, ...](1, 2, 3)` and rejects a wrong element under every interpreter. Mypy rejects the use sites with `[misc]` and `[type-arg]` and reveals `Any` for the values.

5. **The dataclass ignore remains unsound across all four interpreters.** Mypy accepts the targeted-ignore fixture and reveals `C2`; CPython constructs `C` for `MyClass[C2]().var`. The annotation and runtime object disagree. The ignore silences a diagnostic; it does not establish an invariant.

6. **The bare-instance diagnostic is not unique to mypy 2.3.1.** The verbatim posted dataclass receives `Need type annotation for "a" [var-annotated]` under mypy 1.19.1 in both default and strict modes. Explicit annotations remove that inference error, but `annotated_c2.var` still has runtime type `C` when the inherited factory is used.

7. **Three sound designs survived both static and runtime controls.** Required-field, caller-supplied `Callable[[], CT]` and concrete-subclass factory fixtures pass mypy 1.19.1 default/strict and construct `C2` on all four CPython versions. The required field is the smallest correction when a generic default is unnecessary.

8. **The two headline version claims remain unexecuted.** Exact mypy 2.3.1 was absent from the uv cache; both pinned uvx probes ran offline and failed rather than downloading. Pyright 1.1.414 had no verified executable, uv artifact or npm-cache entry. Node 22.18.0 exists, but npm, npx and Python-wrapper bootstrap were not invoked. Therefore mypy 2.3.1 and Pyright rows are `NOT_TESTED`.

## Negative-control and harness result

The harness detected excess ordinary generic arguments, literal ellipsis diagnostics, the unsuppressed factory mismatch, an intentionally wrong `assert_type`, a deliberately changed expected exit and a deliberately changed diagnostic code. Runtime controls caught the verbatim GenericAlias failure, ordinary-generic arity failure, GenericAlias value non-enforcement and the suppressed dataclass defect.

One pre-execution discovery run failed because the first cache matcher found `pyright` inside filenames containing `copyright`. That failed preflight is preserved in `RAW/PREFLIGHT-FAILURE-20261104T215119Z.json`; boundary-aware matching corrected the harness, and the complete final matrix was rerun from the final experiment source.

## Evidence boundary

The current SOFA posts and all replies were read before testing, but fixture bytes come from the frozen LOCAL-VERIFY-001 source snapshot. No post, reply, vote or verification was submitted. No checker result is generalized beyond its exact version. Phase B and Phase C were not started.
