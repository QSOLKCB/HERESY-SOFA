# FUNCTIONAL-GRAPH-001 — Dual-witness reconciliation

**Date:** 5 November 2026 (Australia/Adelaide)  
**Scope:** A static, independent inspection of the seven files supplied in this conversation. The source code was not rerun under the witnesses' original environments by this third reviewer. The two witnesses' `PASS` verdicts are *reported* and supported by internal document consistency, not reproduced machine execution in this session.

## Outcome

**Evidence-integrity PASS (seven supplied files):** all declared file SHA-256 values and byte sizes match independently recomputed values. Both canonical raw JSON files match their corresponding report benchmark tables. The independent benchmark median fields recompute from their stored samples. Both witnesses identify the same source SHA and commit.

- **Monica:** reported 36,749 independently checked graph instances, 183,745 candidate comparisons, 3/3 negative controls rejected, and 7 canonical tests passed.
- **Codex:** reported 46,897 independently checked graph instances, 234,485 candidate comparisons, 4/4 negative controls rejected, and 7 canonical tests passed. Additional independent O(n log n) binary-lifting reference for large random cases.
- **Both:** five candidate algorithms agreed in the reported exercised input family; no reported candidate bug or counterexample. These are finite empirical checks, not a machine-checked universal proof.

## Source pin

- Repository: `QSOLKCB/HERESY-SOFA`
- Merged commit: `42af1d99d736802214ed61ffe950e6ad809b1aee`
- File: `challenges/FUNCTIONAL-GRAPH-001/run.py`
- Source SHA-256: `84ff9073190b28e766df5be53dd43c833ae6e45bd0be6901704c95dd63d3ba85`
- GitHub file blob: `cf52bcc90d469377ea72388aa6447d280adb4e44` (connector source check)

## File-integrity ledger

| Uploaded file | Bytes | Independently verified SHA-256 |
|---|---:|---|
| `FUNCTIONAL-GRAPH-001-MONICA-RAW.json` | 3,752 | `4be4fb07ecf7c026f3115b7108c0faa49977216b1367bd98d36a4ee2761506ff` |
| `FUNCTIONAL-GRAPH-001-MONICA-REPORT.json` | 34,693 | `743671cd5a0dc634d115c8187541ed564c53cb70d61663031bff022f35f2d085` |
| `FUNCTIONAL-GRAPH-001-MONICA-REVIEW.md` | 12,768 | `996d469b5b5e4548a246a360d19fb2d36e51047ecfad453cdbc076dffcd0ab7d` |
| `FUNCTIONAL-GRAPH-001-CODEX-RAW.json` | 3,736 | `4706e8510b470a6cb8bc8c9a79d427dab609ad44a4ae114aaf002ddb135e9a18` |
| `FUNCTIONAL-GRAPH-001-CODEX-ORACLE.py` | 27,068 | `9350de789364f3fd59f5289241163e34df3e8f0c4b4ef2ccfc0d780b8820e76a` |
| `FUNCTIONAL-GRAPH-001-CODEX-REPORT.json` | 110,350 | `f8981551c5ac4c15045ca4c292fe2e91255c998abc97e06f5f7da9a027de0615` |
| `FUNCTIONAL-GRAPH-001-CODEX-REVIEW.md` | 17,675 | `9aa2ac9adf4c3ed34dc9c6ef07e0f6fa25f3e76a07fa6db4d1577778478d9952` |

## Independent performance comparisons

Values below are **independent benchmark medians**, not the canonical runner medians. Monica used 3 samples per candidate/shape on a Cloudflare-named microVM/EPYC platform; Codex used 5 samples per candidate/shape on a native Ryzen host. They must **not** be pooled or interpreted as a host-to-host throughput comparison.

| Topology (100,000 nodes) | Monica fastest (ms) | Codex fastest (ms) | Both lowest traced memory |
|---|---:|---:|---|
| Random | `path_index` 22.140 | `signed_walk` 15.610 | `signed_walk` |
| Big cycle | `signed_walk` 7.009 | `signed_walk` 4.958 | `indegree_peel` |
| Long chain | `signed_walk` 9.335 | `signed_walk` 6.218 | `edge_walk` |
| Star into 2-cycle | `edge_walk` 17.642 | `edge_walk` 13.000 | `signed_walk` |

Speed winners agree on **three of four** shared shapes; random differs. Traced-memory winners agree on **four of four**. No universal fastest or best-memory implementation is established.

## Qualification ledger

**P01 — Provenance / execution environment.** Monica's `environment.execution_mode` says "authorized local Linux workstation", but its raw output and environment record say `Linux-6.18.56-cloudflare-microvm-2026.10.9`, with `AMD EPYC`. That is evidence of a virtualized, Cloudflare-named execution context, not proof of execution on the intended physical local workstation. Preserve the original report; seek a signed clarification or label it as a microVM/virtualized witness in any public summary. Codex separately reports the native Ubuntu 26.04.1 / Ryzen 9 5950X host.

**P02 — Presentation issue.** Monica's `REVIEW.md` lines 64–69 have a four-column memory table but five columns in its rows; times and memory values are mixed. The underlying JSON and surrounding narrative agree on the intended winners. Do not alter the raw hashed witness document; supply an erratum or independently authored corrected table.

**P03 — Supplemental material absent.** Monica's independent `independent_verify.py` and `independent_benchmark.py` were described but not uploaded. Codex's `SHA256SUMS.txt`, `FINALIZATION.json` and other supplementary files in its claimed 23-entry manifest were not uploaded. Only the seven listed files have been independently byte-hashed here. A complete public reproduction package should include the missing source and manifests or explicitly state they were not supplied.

**P04 — Scope and performance.** Both reports correctly limit correctness to the specified no-self-loop functional-graph family. No formal proof assistant, online judge, or GPU/ETQ/E8/quantum speed advantage was demonstrated. `tracemalloc` peak is Python-traced allocation, not total process RSS. Absolute timings from different hardware must not be compared causally.

## Recommended next steps

1. Preserve all seven original files byte-for-byte. Record this reconciliation as a *separate* document rather than editing witness reports.
2. Request Monica to correct the environment classification and provide its independent oracle/benchmark script and JSON outputs. Request the rest of Codex's 23-entry manifest and checksum source files before calling that full package independently verified.
3. Prepare a GitHub evidence-archive PR in HERESY-SOFA after explicitly approving which machine-identifying metadata will be public. Distinguish the native Codex run, the Monica microVM run, and this static reconciliation.
4. Draft a narrowly scoped SOFA reply emphasizing independent checks, graph-counts, negative controls and a clean per-start solution; credit the existing correct O(n) answer. Follow the SOFA no-outbound-link policy and seek exact-text owner approval before publishing.

**Bottom line:** strong and internally consistent dual-witness algorithm evidence; two documentation/provenance items and missing supplemental material should be closed before treating the full bundle as independently reproducible archival evidence.
