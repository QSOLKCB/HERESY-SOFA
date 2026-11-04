The posted loop can starve status polling even in a bounded synthetic model. With one existing in-flight job and one queued URL repeatedly returning 429, `queue.insert(0, u); sleep(...); continue` remains inside the capacity-fill loop and immediately retries the same URL. The Codex controls observed repeated submissions and zero polls until the simulation ceiling. `pop(0)` and `insert(0)` also impose quadratic list movement.

A safer scheduler uses `deque`, explicit task states, independent submit/poll deadlines, and poll-due-first ordering. Honor `Retry-After` when present and apply finite retry and poll ceilings. Treat 503, missing job IDs, and other ambiguous submission outcomes as `uncertain` unless the protocol guarantees rejection or idempotence; reconcile them before blind resubmission. Unknown status and missing-result paths need explicit handling.

This does not establish Internet Archive quotas, account concurrency, the effect of `if_not_archived_within`, or a 900-second server window. Evidence identifiers: CODEX-001 report SHA-256 `3cebb8b7fff60a5344e91f02c531dcbfe23455a83b518630acdc7c007ec33229`; MONICA-001 report SHA-256 `f1d7d424ccb42b3d5d9e06b05b2d18c8bf99a123ab317731f036ad01c4e485ef`.

More edge case Gremlins for the Goblin God!
