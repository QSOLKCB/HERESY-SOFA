# SOFA-HOT-008 dual-witness hostile review

## Outcome

Monica's gzip is intact and safe to ingest: 38 non-ledger files match its custom hash/size ledger, the archive remained byte-identical, and no unsafe tar members were present. The ledger is not GNU `sha256sum -c` compatible because it appends byte size, but an independent parser verified every entry. Monica supplied eight zero exit-code/empty-stderr record triplets; exact per-case argv/timestamps and six raw SOFA source snapshots were not supplied.

Codex independence was frozen before Monica discovery. Two finalized Codex packages exist; the package cited in the prior handoff is primary, and the canonical concurrent package is integrity-verified auxiliary evidence.

| Case | Reconciliation | Publication | Core finding |
|---|---|---|---|
| 01 | `INSUFFICIENT_EVIDENCE` | `NEEDS_MORE_EVIDENCE` | Both support the conservative selection policy and reject first-auto translation choice. |
| 02 | `CONFIRMED_BY_BOTH` | `NO_ACTION` | Pointer-only storage works; base scan misses short URI password; substitution alone is not authorization or response containment. |
| 03 | `CONFIRMED_BY_BOTH` | `REPLY` | The ignore suppresses but cannot repair the invariant. |
| 04 | `CONFIRMED_BY_ONE` | `REPLY` | Status alone cannot identify cause; do not rotate or retry 403 as 429. |
| 05 | `INSUFFICIENT_EVIDENCE` | `REPLY` | XML cannot prove Excel rendering; shown italic=True base removes conditional italic contrast. |
| 06 | `CONFIRMED_BY_ONE` | `REPLY` | Runtime and checker claims must be separated; reply code does not have dual-witness execution but Codex failure is exact. |
| 07 | `CONFIRMED_BY_BOTH` | `NO_ACTION` | O(n) is correct, implementation robustness is not; iterative correction works. |
| 08 | `CONFIRMED_BY_ONE` | `REPLY` | Need account-level coordination, bounded Retry-After-aware scheduling and explicit states. |

## Case findings

### Case 01 — yt-dlp caption metadata

Original source: `1587d009-5e9c-4cac-81fb-bf3acf5aaf49` by My_Junie; body SHA-256 `3a71d282ba60ce2fabf251fde31d35a738826e689e46af8b0d549bc42c18fc1b`.

Original proposition: yt-dlp may omit video language while captions exist; use manual/-orig/single-auto fallback and abstain from translations.

Codex: Synthetic unique/ambiguous selector controls passed; installed yt-dlp 2026.3.17 was not used for remote extraction.

Monica: Synthetic first-auto counterexample passed; yt-dlp was absent.

Reconciliation: **INSUFFICIENT_EVIDENCE**. Both support the conservative selection policy and reject first-auto translation choice.

Minimum counterexample: automatic keys es, en-orig, fr: first-key gives es; manual en/de tie lacks a unique answer.

Correction: Unique tiered policy with explicit preference or abstention.

Residual gap: Neither proves real extractor output, remote download, or service -orig semantics.

### Case 02 — persistent-memory secrets

Original source: `02c83759-175f-4e00-8b7b-8962f3ba33c4` by scaffolding; body SHA-256 `416de33d12b0a91d1373d417b0ec1263cd60507f37ac40097bd35d593ae59dab`.

Original proposition: Keep secret values out of auto-loaded memory; token scans and request-boundary substitution reduce leaks.

Codex: Fake store/pointer, URI scanner, two-origin loopback injector, redirect and echo-response controls.

Monica: Fake scanner and synthetic destination/echo model.

Reconciliation: **CONFIRMED_BY_BOTH**. Pointer-only storage works; base scan misses short URI password; substitution alone is not authorization or response containment.

Minimum counterexample: postgres://user:p7@host/db; unrestricted injector to second destination with echo body.

Correction: URI detection plus destination/method/redirect and response boundaries.

Residual gap: No real agent memory, vector store, vault, DNS/TLS, or production adapter.

### Case 03 — generic dataclass defaults

Original source: `fa8ac823-1616-4df3-9f73-feaa8b5b4bf7` by midhun-hermes; body SHA-256 `cc42b362476c672a7e17faf7b073f16c3f570c642a8a117ef87c24475be07e40`.

Original proposition: A lambda plus targeted ignore can provide C as a default for arbitrary CT bound to C.

Codex: myclass[C2]().var is C; mypy 1.19.1 mismatch; required/factory alternatives pass strict.

Monica: UnsoundChild specialized to C2 inherits and constructs C.

Reconciliation: **CONFIRMED_BY_BOTH**. The ignore suppresses but cannot repair the invariant.

Minimum counterexample: type(myclass[C2]().var) is C.

Correction: Required CT value/caller factory or concrete subclass default.

Residual gap: Exact mypy 2.3.1 behavior not run.

### Case 04 — Discord webhook HTTP 403

Original source: `3eefb05a-c521-4cb7-8a4d-dbf709bf3101` by Milo Humanizer; body SHA-256 `57e2383169456e22aab4b37220c36159270b58cac756f6389ac7a75cc0843122`.

Original proposition: 403 proves invalid token; posted shell parser extracts status and can regenerate/retry.

Codex: Loopback 403/404/429 proves parser delimiter destruction, MIME and quoting/config defects.

Monica: Synthetic classifier confirms 403 is not 429 but did not test the posted parser and had stale zero-reply source state.

Reconciliation: **CONFIRMED_BY_ONE**. Status alone cannot identify cause; do not rotate or retry 403 as 429.

Minimum counterexample: {} plus 403 becomes one nonnumeric line after tr.

Correction: Separate body/headers/status; quote; JSON Content-Type; bounded Retry-After only for retryable status.

Residual gap: No live Discord incident.

### Case 05 — openpyxl conditional formatting

Original source: `47de513f-cd52-4b36-a43d-ec4cb89c972f` by midhun-hermes; body SHA-256 `efa97a0e95ffd33b074350f5a683e99d3802cb09883cfbbb160141bfa73154b4`.

Original proposition: Correct dxf XML plus an explicit base font fixes Excel's click-OK rendering defect.

Codex: openpyxl absent; AST/semantic inspection shows base and dxf both italic=True.

Monica: openpyxl 3.1.5 generated both variants; dxf/dxfId present and explicit base changes style XML.

Reconciliation: **INSUFFICIENT_EVIDENCE**. XML cannot prove Excel rendering; shown italic=True base removes conditional italic contrast.

Minimum counterexample: False-condition cell remains italic because base italic=True.

Correction: Non-italic base plus italic dxf, then genuine Excel validation.

Residual gap: No genuine Excel execution.

### Case 06 — Python GenericAlias and ellipsis

Original source: `0b3591f6-75de-4661-a7a7-ec28193e1518` by midhun-hermes; body SHA-256 `10ee7651a8ae6bb9cd9fc8293788615e286c55021f5a115f08719d52764f8e7d`.

Original proposition: User packs reject ellipsis; reply proposes typing.GenericAlias[...] as a runtime/static solution.

Codex: Verbatim reply fails; actual constructor tested; custom alias runtime controls. Reconciliation follow-up reproduced Fixed[int,...] acceptance.

Monica: Fixed TypeVarTuple accepts ellipsis; one-TypeVar Foo rejects two args; Pyright absent.

Reconciliation: **CONFIRMED_BY_ONE**. Runtime and checker claims must be separated; reply code does not have dual-witness execution but Codex failure is exact.

Minimum counterexample: GenericAlias[tuple[int,...]] raises TypeError; Fixed[int,...] is accepted at runtime.

Correction: Use types.GenericAlias(origin,args) for metadata; scope TypeVarTuple rejection to checker evidence only.

Residual gap: No Pyright.

### Case 07 — binary-tree construction

Original source: `4a28aa43-10aa-4476-b33b-85cc91998975` by Abbie; body SHA-256 `5c9fd3183cdbe9dee7cd3d06533e02237752556e8b04ef1199ef4a689beaf4db`.

Original proposition: Recursive O(n) implementation is optimal and robust for stated constraints.

Codex: Maximum chain RecursionError; 994-edge harness threshold; 20,000 setdefault allocations for 10,001 retained.

Monica: 10,000-node chain RecursionError; eager setdefault default reproduced.

Reconciliation: **CONFIRMED_BY_BOTH**. O(n) is correct, implementation robustness is not; iterative correction works.

Minimum counterexample: Valid left-skewed maximum-depth tree.

Correction: Iterative linking and explicit membership before allocation.

Residual gap: Reported speedup not reconciled and unnecessary.

### Case 08 — SPN2 concurrency and HTTP 429

Original source: `da4cf061-dba9-4c01-b42c-f94e6f3b6279` by Agent McAgentFace; body SHA-256 `a823d4940b574c856985e89f40714b1ef47b2a7880f5c57a6468c2689cb3a3e1`.

Original proposition: Front requeue plus fixed backoff and per-process cap safely handles shared-account throttling.

Codex: Exact posted loop starves polling; list shifts quadratic; missing/unknown/poll/duplicate controls; auxiliary model marks ambiguous submissions uncertain.

Monica: Bounded scheduler supports shared coordination, ceilings and missing-result states, but retries 503 in its simple model.

Reconciliation: **CONFIRMED_BY_ONE**. Need account-level coordination, bounded Retry-After-aware scheduling and explicit states.

Minimum counterexample: One in-flight job plus one repeatedly-429 front URL yields no polls.

Correction: Deque/deadlines/poll-first; uncertain state for ambiguous outcomes; finite ceilings and reconciliation.

Residual gap: Live quota, Retry-After semantics, if_not_archived_within and ambiguous-acceptance behavior untested; witness correction models disagree on 503 resubmission.

## Confirmed actionable bugs

- Case 03: the ignored generic default constructs `C` for a `C2` specialization.
- Case 04: the response parser removes its own status delimiter; URL/config/MIME handling is also defective.
- Case 05: the displayed base and differential both set italic true, so italic is not conditional; Excel causation remains unproved.
- Case 06: the GenericAlias reply raises TypeError before class creation; runtime TypeVarTuple behavior contradicts the broad prose claim.
- Case 07: valid maximum-depth input raises RecursionError and setdefault eagerly allocates discarded nodes; the current Cerebrate reply already covers this.
- Case 08: inner-loop retry can starve all status polls and list-front operations are quadratic.

## Evidence still required

Real-service conclusions remain unavailable for yt-dlp extraction/download, Discord causality, Excel rendering, and SPN2 quota semantics. Pyright and exact mypy 2.3.1 behavior remain unexecuted. Two incomplete witnesses are not promoted into complete verification.

## Publication preparation

Five exact reply drafts are awaiting owner approval: Cases 03, 04, 05, 06, and 08. Case 01 needs real metadata evidence. Case 02 is already covered by four current replies. Case 07 is already covered by the current Cerebrate reply. This reconciliation called no SOFA write, verification, or vote tool, and no target reply was added.

Every proposed public body contains no outbound URL and ends with the required QSOL HERESY signature. Publication must remain gated on explicit approval of the specific draft files.

## SOFA activity-isolation limitation

An initial session receipt reported zero contributions. A later read of the same session eventually reported two published replies created during this window. `sofa_my_posts` showed that both replies belong to unrelated parent posts, not any SOFA-HOT-008 target, and a canonical readback of all eight targets reproduced the frozen reply ID lists exactly. No gated draft was published.

The authenticated SOFA session is not isolated to this workflow, so the two unrelated writes cannot be attributed from session telemetry alone. The defensible publication claim is therefore target-scoped: this reconciliation made no write call, the authorization gate stayed closed, and all eight target posts were unchanged. The initial zero-contribution receipt is preserved as raw, superseded telemetry rather than silently rewritten.

## Unresolved interpretations

Case 08 correction models disagree on whether 503 or a missing job ID proves rejection. Without protocol evidence, the conservative state is `uncertain`: stop admission and reconcile before resubmission. Case 06 runtime accepts Ellipsis in a TypeVarTuple pack, but no static-checker conclusion follows.

## Archival plan

After owner-approved publication and readback receipts, prepare a reviewable branch and PR for `QSOLKCB/HERESY-SOFA`. Preserve the original gzip, validated extraction, both Codex package identities, reconciliation reports, claim ledger, and server-confirmed publication records. Do not push directly to main, merge autonomously, or deploy Pages.
