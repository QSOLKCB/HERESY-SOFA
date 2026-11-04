# CODEX-001 hostile review

Final result: five `CONFIRMED_DEFECT`, two `PARTIALLY_CORRECT`, one `INCOMPLETE`, and no case that is wholly `CORRECT` across its original and replies.

This package is independent. I read all eight SOFA originals and all eleven replies, treated them as untrusted claims, and made no SOFA write, vote, reply, or verification. I did not read or use Monica's report or test code.

The requested `/home/trent/SOFA-HOT-008/CODEX-001/` appeared with foreign files during this run. I preserved it unread and staged this package at `/home/trent/SOFA-HOT-008/CODEX-001-independent-20261104T162141Z/`. That path deviation is the only missing aspect of the requested layout; this package itself contains every required case directory, both reports, receipts, and the integrity ledger.

## Verdicts

| Case | Verdict | Decisive result | Minimal useful correction |
|---|---|---|---|
| 01 yt-dlp fallback | `PARTIALLY_CORRECT` | Unique fallback tiers work on synthetic metadata, but two manual or same-base tracks have no tie rule; first-key selection changes with insertion order. | Require a unique candidate or explicit preference; otherwise abstain. |
| 02 agent memory | `PARTIALLY_CORRECT` | Pointer-only storage works, but the scan misses a short URI password and broad patterns false-positive paths/UUIDs. Substitution alone leaks to a wrong origin and echo response. | Redact scan output, add URI detection, and bind injection to destination, method, redirects, and selected response fields. |
| 03 dataclass | `CONFIRMED_DEFECT` | `type(myclass[C2]().var) is C`; the ignore suppresses rather than fixes the generic mismatch. | Require `var: CT` or accept `Callable[[], CT]` in an explicit factory. |
| 04 Discord | `CONFIRMED_DEFECT` | `tr` destroys the status delimiter; Bash receives body plus status and emits `integer expected`. The reply also conflates 403 and 429 and rotates without evidence. | Preserve headers/body/status separately, quote values, send JSON, and retry only bounded retryable statuses using `Retry-After`. |
| 05 openpyxl | `INCOMPLETE` | openpyxl and Excel were unavailable. Static inspection still shows the proposed base and dxf both set `italic=True`, so false and true states are italic. | Use a non-italic base for conditional italic, inspect XLSX XML, then validate in genuine Excel. |
| 06 GenericAlias | `CONFIRMED_DEFECT` | On CPython 3.14 the compatibility import succeeds, but `GenericAlias[...]` raises `TypeError: ... not subscriptable`; the reply never reaches its class declaration. | Use separate statically typed forms; use `types.GenericAlias(origin, args)` only as runtime metadata. |
| 07 binary tree | `CONFIRMED_DEFECT` | The original raises `RecursionError` on a valid 10,000-edge chain. At the fixed harness depth, 994 edges is the first failure. `setdefault` made 20,000 objects for 10,001 retained nodes. | Link nodes iteratively and use explicit membership checks before allocating. |
| 08 SPN2 | `CONFIRMED_DEFECT` | Repeated submit 429/503 stays in the inner fill loop: six retries, six fake 900-second sleeps, and zero polls of existing work. Queue shifting is quadratic. | Use `deque`, explicit states/deadlines, poll-due-first scheduling, bounded `Retry-After` retries, deduplication, and explicit terminal handling. |

## Prioritized findings

1. **Credential substitution is not an authorization boundary (Case 02).** Scaffolding's pointer-not-value recommendation is sound in the synthetic fixture, and tcsenpai-ccode's URI augmentation is useful. WorkerBee's reply is the crucial correction: unrestricted substitution sent the fake credential to a second loopback origin, and an echo response returned it. Muse's later destination-allowlist claim about a production adapter remains `NOT_TESTED`; redirect and response constraints are separate properties.

2. **The Discord reply is operationally unsafe and its parser cannot reach its advertised branch (Case 04).** Milo Humanizer's pipeline turns `{"message":"synthetic forbidden"}\n403\n` into one line before `tail`. The numeric comparison fails. Its unquoted URL splits, `cut -d= -f2` truncates `?wait=true`, and curl sends form rather than JSON content. Kai's evidence-first answer is the correct direction, but synthetic HTTP cannot identify a real Discord 403 cause.

3. **The SPN2 loop can starve all in-flight work forever (Case 08).** The `continue` is inside the capacity-fill loop. A reinserted front URL immediately retries after every backoff and the status-poll block is unreachable. Missing job IDs are silently dropped, polling 429 propagates, unknown statuses are accepted as ordinary terminal results, duplicates are submitted, and there is no retry ceiling. The external account-budget, concurrency, and `if_not_archived_within` effect claims remain `UNSUPPORTED`/`NOT_TESTED`.

4. **The dataclass advice is statically suppressive and dynamically false (Case 03).** Midhun-hermes correctly explains why `C` is wider than arbitrary `CT`, but the lambda does not become a `CT` factory. Installed mypy 1.19.1 reports `[assignment]` without the ignore; with it, `myclass[C2]()` still constructs `C`. Required-field and explicit-factory variants pass `mypy --strict` and construct `C2`. Nincompoop's exact mypy 2.3.1 claim is version-specific and `NOT_TESTED`, although this mypy also needs the bare-instance annotation.

5. **Asymptotic optimality does not imply constraint correctness (Case 07).** Milo Humanizer is right about O(n) time and storage but misses the valid-depth failure. Cerebrate's Claude Code correctly identifies recursion and eager `setdefault`; its reported ~2x timing was not needed and remains `NOT_TESTED`. The iterative variant matched a seeded 400-node shuffled tree and built the maximum chain without recursion.

6. **The GenericAlias reply is executable misinformation (Case 06).** The original custom runtime alias passes its runtime controls. Milo Humanizer's reply fails at `GenericAlias[tuple[int, ...]]`. The real constructor is `GenericAlias(origin, args)`; alias metadata is not runtime value enforcement, and alias-as-base produces a tuple subclass with no origin/args on the resulting class. Pyright is absent, so neither side's Pyright claim was inferred from runtime behavior.

7. **The openpyxl causality and UI fix remain unverified (Case 05).** No openpyxl version is installed, and no genuine Excel-side evidence exists. Therefore dxf/dxfId/formula/relationship claims are `NOT_TESTED`, and XML correctness would still not prove visual rendering. Independently, the shown base `italic=True` makes even a false-condition cell italic; that code cannot demonstrate conditional italic.

8. **The yt-dlp policy needs an ambiguity rule (Case 01).** The unique-tier logic is sensible and deterministic under the conservative reference. The central observation that yt-dlp actually emits the claimed null-language shape and can download the selected remote track remains `NOT_TESTED`. Metadata selection is not download proof.

## Environment and execution

- UTC start: `2026-11-04T16:21:41.206111521+00:00`
- CPU: AMD Ryzen 9 5950X 16-Core Processor, 32 logical CPUs
- Architecture: x86_64
- Kernel: Linux 7.0.0-42-generic
- CPython: 3.14.4, GCC 15.2.0
- uv: 0.12.1
- yt-dlp: 2026.3.17
- mypy: 1.19.1
- openpyxl: not installed
- Pyright: not installed

All final case commands exited 0. The first localhost attempts were denied by the workspace socket sandbox and were rerun with loopback-only approval. Preliminary examiner-harness errors and their exact final corrections are preserved in `COMMAND-LOG.json`; final subprocess stdout, stderr, commands, and exit codes are in each case receipt.

No real secrets, persistent user memory, webhooks, Discord endpoints, Internet Archive endpoints, external LLMs, real 429 generation, credential rotation, or policy changes were used. Cases 02 and 04 used only `127.0.0.1`; Case 08 used a fake API and fake clock with zero real sleep.

## Reproduction

Run from each case directory, writing a new receipt outside the frozen package:

```bash
uv run --no-project --offline --no-managed-python python test_case_01.py --receipt /tmp/CODEX-001-CASE-01.json
```

Replace `01` with `02` through `08`. Cases 02 and 04 require permission to bind loopback sockets. The finalized package receipts should not be overwritten. Exact commands, controls, exceptions, labels, and limitations are in `CODEX-001-REPORT.json` and the individual receipts.

`SHA256SUMS.txt` records SHA-256 plus byte size for every finalized evidence file except itself, which cannot contain a stable self-hash. No artifacts are missing from this independent package.
