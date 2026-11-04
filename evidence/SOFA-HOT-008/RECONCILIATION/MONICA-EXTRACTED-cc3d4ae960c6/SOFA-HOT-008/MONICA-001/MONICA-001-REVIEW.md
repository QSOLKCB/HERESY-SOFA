# SOFA-HOT-008 / MONICA-001 — Independent Eight-Case Adversarial Review

## Executive result

**Overall status: PARTIAL.** All eight self-authored offline test programs completed under CPython 3.14.4 with exit code 0 after their assertions passed; however, several requested claims depend on packages or services that were not available or were deliberately not contacted. The execution environment reported `container-other`, so this is virtualized local execution, **not native physical-workstation testing**. Seed: **51120268**. No Codex materials were inspected.

| Rank | Case ID | Subject | Status | Recommendation |
| ---: | --- | --- | --- | --- |
| 1 | `1587d009-5e9c-4cac-81fb-bf3acf5aaf49` | yt-dlp captions | **PARTIAL** | **VERIFY** |
| 2 | `02c83759-175f-4e00-8b7b-8962f3ba33c4` | agent-memory secrets | **PASS** | **REPLY** |
| 3 | `fa8ac823-1616-4df3-9f73-feaa8b5b4bf7` | bound generic dataclass | **PARTIAL** | **REPLY** |
| 4 | `3eefb05a-c521-4cb7-8a4d-dbf709bf3101` | Discord webhook 403 | **PARTIAL** | **NO_ACTION** |
| 5 | `47de513f-cd52-4b36-a43d-ec4cb89c972f` | openpyxl conditional fonts | **PARTIAL** | **VERIFY** |
| 6 | `0b3591f6-75de-4661-a7a7-ec28193e1518` | GenericAlias / ellipsis | **PARTIAL** | **VERIFY** |
| 7 | `4a28aa43-10aa-4476-b33b-85cc91998975` | binary-tree construction | **PASS** | **REPLY** |
| 8 | `da4cf061-dba9-4c01-b42c-f94e6f3b6279` | SPN2 concurrency/rate limiting | **PARTIAL** | **REPLY** |

## Adverse findings

### 1. yt-dlp captions — PARTIAL / VERIFY

The synthetic selector demonstrates two real logical hazards: `language` and `original_language` can be absent while `subtitles` has `de-DE`, and selecting the first automatic key from `{es, en-orig, fr}` returns `es` rather than the intended original-language ASR track. The evidence supports the conservative manual-first, `-orig`-before-single-auto policy at the metadata level. **It does not establish real yt-dlp extractor behavior**, because yt-dlp was unavailable and was not installed. Preserve a no-random-translation fallback; verify against saved, real metadata fixtures before publishing stronger claims.

### 2. Agent-memory secrets — PASS / REPLY

The original scanner patterns detected the fake Bearer, `api_key`, and private-key header, but missed `postgres://user:pw7@db.invalid/a`; an augmented URI-credential shape detected it. A separate synthetic counterexample showed unrestricted placeholder substitution delivers a fake credential to `attacker.invalid`, and an unfiltered echo response returns it. Therefore, placeholder substitution is not destination authorization and does not by itself contain response/log exposure. A defensible correction is destination/path validation before injection, redirect policy, and selected/sanitized response fields. Existing replies already raise these limits, so a reply should add only independently executed counterexamples and avoid claims about any real wrapper.

### 3. Generic dataclass — PARTIAL / REPLY

The claimed lambda-plus-ignore arrangement is demonstrably unsound as a generic invariant: `UnsoundChild` specializes `CT` as `C2`, yet inherits a factory that yields `C`. The runtime test observed exactly that base object. `# type: ignore` can suppress a checker complaint; it cannot change runtime construction or make `C` a `C2`. Require a caller-supplied value/factory in the generic base, or give every concrete subclass its own matching default factory. Mypy and Pyright were both absent, so every static-checker claim is **NOT_TESTED**.

### 4. Discord 403 — PARTIAL / NO_ACTION

The synthetic response model differentiated 403 with Missing Access, generic 403, 429 with/without Retry-After, 404, and 401. This validates that status 403 must not be retried as though it were rate limiting and cannot by itself identify revocation, missing permission, or intermediary behavior. The test also used argv construction rather than shell interpolation and rejected an unapproved destination shape. There was no Discord request. The retrieved original question had **0 answers**, so no answer claim exists to correct; retain this as a diagnostic checklist rather than publish a causal explanation.

### 5. openpyxl conditional fonts — PARTIAL / VERIFY

Using installed openpyxl 3.1.5, the test confirmed that both implicit-base and explicit-base workbooks serialize a differential italic font and a `cfRule` with `dxfId`. The explicit font changes base-cell style XML. That is **not** evidence that Excel visibly applies the rule, nor proof that an explicit italic base font causes a click-OK issue to disappear. Excel was unavailable; LibreOffice was deliberately not substituted. The only verified correction is to downgrade the claim to XML serialization; controlled Excel-version evidence is required for the UI claim.

### 6. GenericAlias / ellipsis — PARTIAL / VERIFY

CPython 3.14.4 produced `types.GenericAlias` for `tuple[int, ...]`. It accepted `Fixed[int, ...]` where `Fixed` has a TypeVarTuple pack, but rejected `Foo[int, ...]` for a one-TypeVar class with `TypeError: Too many arguments ... actual 2, expected 1`. Thus, runtime is nuanced and cannot prove the reported Pyright diagnostics. Pyright was absent and not installed: **NOT_TESTED**. A future response must clearly separate CPython runtime behavior, `typing` internal aliases, a custom runtime alias, and checker behavior.

### 7. Binary tree — PASS / REPLY

The original examples and a seeded shuffled variant matched an independent iterative reference. The adversarial valid input was a 10,000-node left-skewed tree; the recursive submitted pattern raised `RecursionError` under the default CPython limit, while iterative construction succeeded. This is a constraint-level correctness/robustness failure despite O(n) asymptotic complexity. The test also showed that `dict.setdefault(key, default())` evaluates the default construction even when the existing value is retained, producing a discarded `Node`. The existing reply correctly states O(n), but overlooks the depth hazard. Prefer iterative node-linking with a children set and root lookup.

### 8. SPN2 concurrency — PARTIAL / REPLY

The offline finite-state scheduler establishes that two workers with per-process cap 3 can create six aggregate in-flight requests against an account capacity of 3; per-process caps cannot enforce per-account coordination. The model also makes permanent 429 transition to `retry_exhausted` with bounded retries, classifies a successful status lacking result data as `missing_result`, and classifies an explicit status error. This challenges sufficiency of a fixed 900-second unbounded retry loop. It does **not** establish real SPN2 limits, `Retry-After`, `if_not_archived_within`, or response semantics. A correction should use shared per-account coordination, bounded retries with jitter/fairness, Retry-After when supplied, and explicit submit/status/result state handling.

## Evidence boundary and publication recommendation

All test programs, per-case JSON outputs, standard-error captures, exit codes, environment record, source snapshots where retained, this review, the machine report, and a final SHA-256 manifest are contained in this package. The audit used fake secrets and mocked responses only. No actual credentials, memory files, accounts, Discord webhook, or Internet Archive endpoint were accessed.

Any later human-reviewed SOFA contribution should contain **no outbound clickable URLs** and should state the exact SOFA case ID, source title, execution environment, local interpreter version, input, observed output, and limit. It should not promote simulated results to service observations or absence of a package to passing coverage.
