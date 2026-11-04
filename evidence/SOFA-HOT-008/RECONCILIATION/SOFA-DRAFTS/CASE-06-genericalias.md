The `GenericAlias` reply does not run as written. On CPython 3.11.15 and 3.14.4, importing `GenericAlias` through `typing` succeeds as a compatibility export, but `GenericAlias[tuple[int, ...]]` raises `TypeError` because `types.GenericAlias` is not subscriptable. The class declaration is therefore never reached. The actual runtime constructor is `types.GenericAlias(origin, args)`, and its metadata does not enforce element types.

A reconciliation follow-up also reproduced an important runtime distinction: a `Generic[Unpack[Ts]]` class accepts `Fixed[int, ...]` on CPython 3.14.4, while a one-`TypeVar` class rejects `Foo[int, ...]` as two arguments. That runtime result neither establishes nor refutes Pyright diagnostics; Pyright was unavailable in both witness environments.

Minimum correction: keep CPython runtime alias behavior, custom validation, and static-checker behavior as separate claims. Evidence identifiers: `CODEX-RECONCILIATION-TEST-CASE-06-TYPEVARTUPLE`; CODEX-001 report SHA-256 `3cebb8b7fff60a5344e91f02c531dcbfe23455a83b518630acdc7c007ec33229`.

More edge case Gremlins for the Goblin God!
