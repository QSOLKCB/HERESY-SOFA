The base-class ignore is not sound for a parameterized runtime instance. On CPython 3.14.4, `myclass[C2]()` still runs the inherited `lambda: C()` factory, so `type(myclass[C2]().var) is C`, not `C2`. A concrete child that overrides the field with `default_factory=C2` is safe, but that does not repair direct `myclass[C2]()` construction.

With mypy 1.19.1, removing the ignore reports the factory assignment mismatch. The targeted ignore can silence that diagnostic, but it cannot change the runtime object. Required-field and explicit `Callable[[], CT]` factory designs both constructed `C2` and passed strict checking in the Codex witness; Monica independently reproduced the inherited-default counterexample at runtime.

Minimum correction: make `var: CT` required in the generic base, or require a caller-supplied typed factory. If a default exists only in a concrete subclass, override both the annotation and factory there. Evidence identifiers: CODEX-001 report SHA-256 `3cebb8b7fff60a5344e91f02c531dcbfe23455a83b518630acdc7c007ec33229`; MONICA-001 report SHA-256 `f1d7d424ccb42b3d5d9e06b05b2d18c8bf99a123ab317731f036ad01c4e485ef`.

More edge case Gremlins for the Goblin God!
