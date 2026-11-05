# LOCAL-VERIFY-002B hostile static-checker review

## Verdict

The two missing checker matrices are now executed, not inferred. Mypy 2.3.1 and Pyright 1.1.414 were run in 112 fresh offline processes over the 14 byte-identified LOCAL-VERIFY-002 fixtures. Both repetitions were semantically identical, all 12 negative controls fired, and no frozen fixture or historical evidence changed.

The headline defect survives: `typing.GenericAlias` is not the proposed generic base, and the runtime `types.GenericAlias(origin, args)` constructor does not provide useful static specialization. Literal ellipsis remains a CPython-runtime-versus-static-checker boundary for the tested user-defined `Generic[*Ts]` form. The generic dataclass factory remains unsound after suppression.

## Baseline and package custody

PR #19 was read back as merged at head `98054e2f4002b63bc724882bd6ee86f45f4fdb28` with merge commit `1ad645e13277a28ba511cad2f6bd2f5d988894d8`. This campaign branched from that exact current `origin/main`. Frozen `evidence/LOCAL-VERIFY-002` has no diff from the source commit; its report remains SHA-256 `70f846f41b6d1da12c1e84b3de403ef631cf30dc8447b7a233cb284d758b5009`.

Acquisition and execution were separated. Seven exact distribution archives were downloaded from their official registries, member-inspected with path/type/size bounds, hash-checked against registry metadata, and archived. Pyright was unpacked by a controlled standard-library extractor; no npm, npx or package lifecycle script ran. Mypy used a six-wheel venv without system site-packages, and `uv pip check` reported compatibility before the canonical matrix.

## GenericAlias and variadic typing

- **Original reply (GA01): rejected by both.** Mypy reports `attr-defined;type-arg`; Pyright reports `reportAttributeAccessIssue`. This agrees with the prior CPython failure, which occurred before the proposed class declaration.
- **Correct runtime constructor (GA02): static dead end.** CPython previously constructed `types.GenericAlias(tuple, (int, Ellipsis))`. Mypy 2.3.1 nevertheless reports `[operator]`, reveals the alias as `types.GenericAlias`, and reduces the call result to `Any`. Pyright reports `reportCallIssue`, knows only `GenericAlias`, and reduces the result to `Unknown`.
- **Custom `__class_getitem__` (GA04): not a typing-language extension.** The runtime hook executes in the frozen runtime evidence, but mypy reports `attr-defined;misc;type-arg` and Pyright reports `reportAttributeAccessIssue;reportInvalidTypeArguments;reportInvalidTypeForm` at the use site.
- **Literal ellipsis in `Generic[*Ts]` (GA05): rejected by both.** Mypy emits `[misc] Unexpected "..."`; Pyright emits `reportInvalidTypeForm`. Pyright's reveal text retains `Packed[int, ...]`, but that information diagnostic does not cancel the error. Runtime acceptance is not static acceptance.
- **Ordinary excess arity (GA06): rejected by both**, validating the negative-control path.

## Generic dataclass invariant

- **Bare original fixture (DC01): checker disagreement preserved.** Mypy 2.3.1 reproduces `[var-annotated]` in default and strict modes. Pyright standard accepts it, while strict reports Unknown-related diagnostics. Neither outcome repairs runtime construction.
- **Unsuppressed mismatch (DC02): both checkers catch it.** Mypy reports `[assignment]`; Pyright reports `reportAssignmentType`. Both reveal `value.var` as `C2`, while the prior native execution shows that the default factory actually constructs `C`.
- **Targeted ignore (DC03): diagnostic silence is not correctness.** Mypy accepts in both modes and reveals `C2`; Pyright standard also accepts. Pyright strict's sole error is the unrelated `reportUnnecessaryIsInstance`. The native runtime counterexample remains `MyClass[C2]().var -> C`.
- **Sound designs (DC04–DC06): confirmed.** Required-field construction, a caller-supplied typed factory and a concrete subclass factory all pass both mypy modes and both Pyright modes, reveal `C2`, and agree with the prior runtime `C2` results.
- **Bare inference (DC07): not equivalent to specialization.** Mypy rejects the bare generic; Pyright standard records `MyClass[Unknown]`, and strict rejects the unknowns. Explicit annotation can still tell either checker `C2` while the defective factory returns `C`.

## Controls and reproducibility

- Final matrix rows: 56.
- Fresh checker processes: 112.
- Negative controls: 12 passed, zero failed.
- Timeouts: zero.
- Repeat comparison: all 56 semantic pairs identical. Pyright's wall-clock and duration fields are preserved but excluded from semantic equality.
- Frozen source: unchanged before/after execution.
- Network during checker execution: none.

Two pre-finalization harness corrections are preserved rather than hidden: distribution-name normalization in the archive validator, and optional mypy column numbers in the diagnostic parser. A valid intermediate run that inherited three system packages is also identified as superseded; the canonical run uses only archived wheels.

## Minimal corrections

For runtime alias metadata, call `types.GenericAlias(origin, args)` and do not claim that it creates a statically useful generic class. For a typed variadic class, use `TypeVarTuple` with actual type arguments; do not use literal ellipsis in this tested user-defined form. For the dataclass, require the field, accept a `Callable[[], CT]`, or override annotation and factory together in a concrete subclass. A targeted ignore is not a constructor.

## Limits

This addendum executes static checkers only. CPython runtime observations are cited from immutable LOCAL-VERIFY-002 and were not rerun. The results cover mypy 2.3.1, Pyright 1.1.414, Python target 3.14 and the recorded default/strict configurations; they are not universal claims about future releases. No SOFA content was changed.
