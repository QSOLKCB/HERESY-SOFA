# Local testing backlog

Every item below is **`NOT_EXECUTED`** in this archival PR. The table defines a future evidence contract; it is not a test receipt or authorization to access production systems.

## SOFA-HOT-008

### HOT-01 — yt-dlp extraction, download and multilingual metadata

- **Status:** `NOT_EXECUTED`.
- **Prerequisites:** pinned yt-dlp release; authorized public videos with manual captions, automatic `-orig` tracks, translated maps, missing video language and deliberately ambiguous choices; no account credentials.
- **Expected evidence:** saved `--dump-single-json`/extractor metadata; exact selected/abstained language; separate subtitle-download exit code, headers and resulting file hash; tool and interpreter versions.
- **Negative controls:** two manual tracks without a preference; multiple automatic tracks without unique `-orig`; translated/non-caption entries; selected metadata URL returning an error; video-language value present and absent.
- **Platform:** supported Linux/macOS/Windows runner with network isolation and disposable output.
- **Live external access:** **yes**, to the authorized media host; metadata policy can also be replayed offline from frozen fixtures.

### HOT-02 — genuine Excel rendering of openpyxl conditional fonts

- **Status:** `NOT_EXECUTED`.
- **Prerequisites:** pinned openpyxl and CPython versions; genuine supported Microsoft Excel build on Windows or macOS; disposable workbooks with recorded XML.
- **Expected evidence:** workbook hashes; `styles.xml`, worksheet formula, base style and `dxfId`; Excel build/version; observed render before and after recalculation/dialog interaction; condition-true and condition-false results.
- **Negative controls:** base `italic=True` with differential `italic=True`; explicit base `italic=False`; false formulas; wrong range/formula anchor; identical XML opened without Excel-side recalculation.
- **Platform:** genuine Excel. LibreOffice is not a substitute.
- **Live external access:** no, aside from licensed software acquisition/activation already available to the tester.

### HOT-03 — Discord causality versus the synthetic shell-parser defect

- **Status:** `NOT_EXECUTED`.
- **Prerequisites:** owner-authorized disposable webhook/channel, redacted logging, bounded request count, administrator access to relevant audit information and an approved test window.
- **Expected evidence:** exact sanitized request argv, status, response Content-Type, redacted body category, request/edge IDs and retry headers; separate proof that the corrected parser extracts 403/404/429 without conflation.
- **Negative controls:** local 403/404/429 fixtures; HTML intermediary body versus structured service JSON; malformed JSON MIME; URL containing `=` or whitespace; terminal 403 versus bounded 429 handling.
- **Platform:** local shell/parser tests plus an authorized network client.
- **Live external access:** **yes** for service causality; **no** for the already reproduced parser defect. Never use a production webhook or log its token.

### HOT-04 — Internet Archive SPN2 quotas and concurrency semantics

- **Status:** `NOT_EXECUTED`.
- **Prerequisites:** explicit Internet Archive test authorization/account, non-sensitive test URLs, bounded request budget and stop conditions.
- **Expected evidence:** per-request UTC times, status/headers including `Retry-After`, job IDs, poll transitions, duplicate-capture result, process/account concurrency and a server-confirmed terminal outcome.
- **Negative controls:** deterministic fake API for repeated 429/503, delayed acceptance, missing job ID, duplicate URL, unknown status and poll errors; single-process versus coordinated multi-process scheduler.
- **Platform:** offline finite-state simulator first; authorized network runner only after review.
- **Live external access:** **yes** to establish real quota/protocol semantics. Synthetic results alone remain simulation evidence.

### HOT-05 — mypy 2.3.1 and Pyright compatibility

- **Status:** `NOT_EXECUTED`.
- **Prerequisites:** already available or separately approved pinned mypy 2.3.1 and Pyright version; exact preserved snippets; no package download during the evidence run.
- **Expected evidence:** version commands, exact argv, stdout/stderr and exit codes for original, ignored, required-field, typed-factory, `TypeVarTuple`, one-`TypeVar` and custom-alias files.
- **Negative controls:** remove the ignore; specialize the base directly as `myclass[C2]`; use `Fixed[int, ...]` and `Foo[int, ...]`; corrupt an expected diagnostic so the harness must fail.
- **Platform:** CPython-compatible host for mypy; Pyright requires its supported runtime/toolchain.
- **Live external access:** no after tools are pinned locally.

### HOT-06 — uncertain submissions and missing SPN2 job identifiers

- **Status:** `NOT_EXECUTED`.
- **Prerequisites:** documented idempotency/acceptance contract or authorized test API; explicit finite-state specification and fake clock.
- **Expected evidence:** state transition for every submit/poll response, reconciliation key, retry ceiling, deadline and final classification; proof that ambiguous acceptance is not blindly duplicated.
- **Negative controls:** connection loss after server acceptance, 503 with accepted work, response without job ID, invalid `Retry-After`, repeated unknown status and duplicate input.
- **Platform:** standard-library simulator; live protocol check only after service authorization.
- **Live external access:** optional for scheduler logic, **required** to settle actual service semantics.

## SOFA-BAKERS-DOZEN-013

### BAKERS-01 — SwiftData dual-uniqueness collision

- **Status:** `NOT_EXECUTED`.
- **Prerequisites:** supported macOS/iOS release, matching Xcode/SwiftData toolchain, disposable persistent store and exact model/migration definitions.
- **Expected evidence:** source commit, OS/toolchain versions, store schema, inserts/updates, thrown errors, saved UUID/payload identities and post-reopen state.
- **Negative controls:** collision on each unique field separately; collision split across two existing rows; no-collision insert; transaction rollback; migration/reopen.
- **Platform:** real supported Apple environment.
- **Live external access:** no.

### BAKERS-02 — Windows 11 secure-desktop and sign-in recovery

- **Status:** `NOT_EXECUTED`.
- **Prerequisites:** sacrificial Windows 11 VM or authorized noncritical machine, snapshots, alternate administrator recovery path and a stop rule preventing lockout.
- **Expected evidence:** Windows build, reproduction steps, visible credential-provider state, relevant sanitized logs and which bounded recovery action restored the tile without data loss.
- **Negative controls:** network unavailable, service restart ineffective, ordinary lock screen, Fast User Switching, resume without defect and deliberately unavailable recovery option.
- **Platform:** native Windows 11; Linux documentation review is insufficient.
- **Live external access:** normally no; account/network-dependent variants require separately authorized connectivity.

### BAKERS-03 — Windows session-state event correlation

- **Status:** `NOT_EXECUTED`.
- **Prerequisites:** native Windows host, labelled console/RDP users, Security audit policy, WTS snapshot collector and a disposable event consumer.
- **Expected evidence:** raw event/channel/version/record IDs, WTS snapshots, boot/session generations, expected versus reduced transitions and exact C# monitor output.
- **Negative controls:** network/service/batch 4624, duplicated/out-of-order records, lock without logoff, disconnect/reconnect, Fast User Switching, event-log clear/wrap and reboot/session-ID reuse.
- **Platform:** native Windows with supported APIs.
- **Live external access:** no for local/RDP-loopback fixtures; remote-domain variants require separate authorization.

### BAKERS-04 — Himalaya/Ortie version and OAuth integration

- **Status:** `NOT_EXECUTED`.
- **Prerequisites:** pinned Himalaya and Ortie binaries, matching documentation/config schema, disposable Outlook.com test mailbox, owner-controlled Microsoft application registration and suitable authorized test credentials.
- **Expected evidence:** binary hashes/versions, redacted config parse, `--help` command identity, device/browser consent result, mailbox-list probe, refresh-token rotation and clean unattended renewal failure handling.
- **Negative controls:** v1 config passed to v2 and vice versa; undocumented Ortie command; bare instead of resource-qualified scope; missing `offline_access`; expired/revoked token; replacement token not persisted; secret redaction checks.
- **Platform:** a supported Himalaya/Ortie host and Microsoft identity platform.
- **Live external access:** **yes**. Never reuse personal/production credentials or commit tokens.

### BAKERS-05 — real-world observation-only identity resolution

- **Status:** `NOT_EXECUTED`.
- **Prerequisites:** lawfully accessible frozen public records, independently labelled namesake/handle-change cases, source capture policy and privacy review.
- **Expected evidence:** immutable source digests, edge-level grades, observed versus inferred namespaces, blinded match evaluation and false-link/false-nonlink counts.
- **Negative controls:** namesakes, recycled handles, redirects, copied aggregator stories, missing panel assignments, corrected records and event-level roles that must not imply project-level judging.
- **Platform:** offline evaluation after approved source capture.
- **Live external access:** **yes** for source collection; the evaluation itself should be offline.

### BAKERS-06 — workflow-first prototype comparative study

- **Status:** `NOT_EXECUTED`.
- **Prerequisites:** pre-registered task set, representative consenting users, matched workflow-first/functionality-first slices, defined risk thresholds and privacy review.
- **Expected evidence:** sample sizes, task/order assignment, total engineering effort including prototypes, decision correctness, unauthorized-action count, recovery outcomes and uncertainty intervals.
- **Negative controls:** planted bad recommendation, stale approval digest, changed target after approval, unanswered timeout, duplicate execution and infeasible backend spike.
- **Platform:** project-appropriate user-research environment; mocked external effects only until explicitly authorized.
- **Live external access:** no for the prototype study unless a later separately approved phase tests real integrations.

### BAKERS-07 — race-resistant Bash cleanup boundary

- **Status:** `NOT_EXECUTED`.
- **Prerequisites:** disposable Linux mount/user namespace, descriptor-relative deletion prototype, hard timeouts and no host or production paths.
- **Expected evidence:** deterministic ancestor-swap/symlink race, exact deletion targets, syscall trace, refusal/exit status and comparison with the documented non-adversarial `realpath` guard.
- **Negative controls:** `..` traversal, parent symlink, final symlink, mount replacement, rename between check and deletion, failed deletion command and untrusted root variable.
- **Platform:** isolated Linux fixture with sufficient namespace support.
- **Live external access:** no.

## Scheduling boundary

This file is a review queue only. No item runs in CI, in the background, or as part of this archival PR. Any future live-service, credentialed, Apple or Windows investigation needs separate owner authorization and a new evidence package.
