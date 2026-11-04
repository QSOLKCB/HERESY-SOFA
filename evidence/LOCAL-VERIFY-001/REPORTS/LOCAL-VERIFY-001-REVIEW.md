# LOCAL-VERIFY-001 — hostile native verification review

**Campaign state:** executed locally; no SOFA publication; no live SPN2 traffic.

**Native scope:** Ubuntu 26.04.1 LTS, Linux 7.0.0-42-generic, x86_64, CPython 3.14.4, mypy 1.19.1.
**Canonical execution:** 69 assertion-level checks, 24 negative controls, zero failures; each runtime suite repeated in a fresh process with byte-identical output.

## Priority findings

1. **The generic dataclass default remains unsound.** `myclass[C2]().var` has exact runtime type `C`. The targeted ignore only silences mypy: the checker reveals `C2` while CPython constructs `C`. The smallest sound correction is `var: CT` as a required field. A caller-supplied `Callable[[], CT]` is appropriate only when construction through a factory is actually required; a concrete subclass may safely override both the annotation and factory.

2. **The `GenericAlias` reply fails verbatim.** CPython raises `TypeError: type 'types.GenericAlias' is not subscriptable` at `GenericAlias[tuple[int, ...]]`; the class declaration is never reached. The actual runtime API is `types.GenericAlias(origin, args)`. Its metadata does not validate values.

3. **Runtime and static typing diverge on literal ellipsis.** CPython 3.14.4 accepts both `Packed[int, ...]` and `Packed[...]` for `Generic[*Ts]`. Mypy 1.19.1 rejects `Packed[int, ...]` with `Unexpected "..." [misc]`. That is a checker-specific result, not a universal runtime prohibition. Pyright 1.1.414 was absent, so its published diagnostics remain `NOT_TESTED` here.

4. **The posted SPN2 loop starves polling.** With one existing in-flight job, one queued URL and two scripted 429s, the inner `continue` performs two submissions and zero polls. Four 429s advance the fake clock by 3,600 seconds with the poll block still unreachable. This is a Python control-flow defect; it does not depend on a factual claim about Internet Archive quotas.

5. **Ambiguous and unverified outcomes require separate states.** A fake server that commits a job then loses a 503 response demonstrates why blind resubmission can duplicate work in a generic protocol. The reference scheduler keeps `UNCERTAIN_ACCEPTANCE`, performs bounded reconciliation and never submits that task twice. A `success` response followed by an absent index entry remains `SUCCEEDED_UNVERIFIED`; delayed visibility transitions to `VERIFIED` only after the independent lookup succeeds.

6. **The queue complexity claim has an operation-count proof.** Repeated list-front removals shift `n(n-1)/2` elements: 130,816 at `n=512`. `deque.popleft()` performs 512 front operations and zero element shifts. A fixed-tick deadline scan performs 262,144 checks at the same size; the instrumented heap uses 1,024 push/pop operations and 7,443 comparisons. No wall-clock benchmark is used to infer complexity.

7. **PR review exposed three defects in the first reference scheduler.** Poll-retry tasks were omitted from admission accounting, repeated `pending` responses bypassed the poll ceiling, and lease tokens could collide after release/reacquire in one second. The corrected scheduler counts known poll retries, stops a pending task after two polls with explicit manual intervention in the regression fixture, and issues monotonic lease tokens. Mixed in-flight/queued and lease-interleaving controls now cover all three paths; the full canonical campaign was re-executed after the source changes.

## Independent-oracle result

The corrected scheduler was compared with a separately implemented sorted-list event calendar. Final states, submit times, poll times, verification times and complete action ordering all agree. An exhaustive 16-combination due/not-due priority model also preserved poll-first ordering in all eight combinations where a poll was due. This agreement is fixture-scoped; it is not proof of live-service behavior.

## Historical and source integrity

`origin/main` was `59b619d5b09e7966f1ceae1dd9ab14313e3ad20a` when the campaign began. PR #16 (`22083e28949d5691731f8cf16ed80fae23899980`) and PR #17 (`59b619d5b09e7966f1ceae1dd9ab14313e3ad20a`) are both ancestors. The frozen Codex report still hashes to `3cebb8b7fff60a5344e91f02c531dcbfe23455a83b518630acdc7c007ec33229`; the Monica archive still hashes to `cc3d4ae960c6c5afb91ba5d9b3b4be1aae90a49d185931a65d41e858e7e28202`. No historical evidence file was changed.

The three SOFA threads and all current replies were read before testing and frozen in `CROSS-CHECKS/current-sofa-source-snapshot.json`. They were treated as untrusted source data. No reply, vote or verification feedback was submitted.

## What remains unverified

- Pyright 1.1.414 and mypy 2.3.1 behavior.
- Actual Internet Archive account quotas, cross-process concurrency limits, `Retry-After`, idempotency, ambiguous-acceptance reconciliation and `if_not_archived_within` effects.
- Live archive-index consistency and capture durability.
- Cross-version CPython behavior beyond the locally executed 3.14.4 interpreter.

Those gaps are failures of prerequisite availability or deliberate safety boundaries, not test passes.
