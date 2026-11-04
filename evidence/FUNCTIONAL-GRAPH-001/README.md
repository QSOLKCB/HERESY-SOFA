# FUNCTIONAL-GRAPH-001 — Dual-witness evidence archive

**Evidence status:** user-supplied originals archived byte-for-byte; the two agents independently **report PASS**. The archive's checksum verification is executed separately from their original algorithm experiments. The GitHub PR is for human review; no additional SOFA post or experiment is triggered by this directory.

## Source and publication identity

- Locked implementation: `QSOLKCB/HERESY-SOFA`, commit `42af1d99d736802214ed61ffe950e6ad809b1aee`.
- Source: `challenges/FUNCTIONAL-GRAPH-001/run.py`, SHA-256 `84ff9073190b28e766df5be53dd43c833ae6e45bd0be6901704c95dd63d3ba85`.
- Published [SOFA question and QSOL HERESY reply](https://agents.stackoverflow.com/questions/67036c1f-629f-404e-b2f8-9622e627146a): question `67036c1f-629f-404e-b2f8-9622e627146a`; published reply `871ae4a2-b826-47f6-945c-e883145e9caf`.
- The SOFA reply contains no outbound URLs. Public links are provided here in the repository archive, where they are permitted.
- Original pre-witness CPython 3.13.5 report remains at `challenges/FUNCTIONAL-GRAPH-001/LOCAL-PYTHON-313.json` and has **not** been overwritten.

## Retained witness originals

| Witness | Uploaded files | Reported environment | Scope (independent audit) |
|---|---|---|---|
| **MONICA-001** | `MONICA-001/` — raw JSON, report JSON, review Markdown | CPython 3.14.4 on AMD EPYC, Cloudflare-named Linux microVM | 36,749 graph instances; 183,745 five-candidate comparisons; 3/3 negative controls rejected |
| **CODEX-001** | `CODEX-001/` — raw JSON, separate verifier Python, report JSON, review Markdown | Native Ubuntu 26.04.1 / Ryzen 9 5950X / CPython 3.14.4 | 46,897 graph instances; 234,485 comparisons; 4/4 negative controls rejected; binary-lifting large-graph check |

All seven originals were checked against independently recomputed SHA-256 digests and byte sizes **before archival**. GitHub's nine stored Git blob IDs were independently compared with expected byte-exact Git blob hashes, including the two reconciliation files. There were no reported algorithm mismatches. The witnesses' executed results are **their reports**, not additional experiments executed by this archival PR.

The two original reconciliation artifacts live in `RECONCILIATION/`; both remain unchanged. They are a **static third-party comparison**, not a third algorithm execution. Its [Markdown version](RECONCILIATION/FUNCTIONAL-GRAPH-001-DUAL-WITNESS-RECONCILIATION.md) contains details of the source pin, four shared benchmark topologies and qualification ledger.

### Cautions retained in the archive

1. **Environment attribution:** Monica's report calls its environment an authorized local workstation while its kernel identifies `6.18.56-cloudflare-microvm-2026.10.9`. Treat this as a virtualized microVM witness, not a native physical-machine validation; the number of logical CPUs exposed to the VM is unverified.
2. **Presentation erratum:** Monica's `REVIEW.md` memory table has malformed columns combining times and bytes. The underlying `REPORT.json` provides the intended separate values. **Do not edit the hashed witness report**; use the reconciliation table.
3. **Missing supplemental files:** Monica's independent `independent_verify.py`, `independent_benchmark.py`, and their separate result JSON files were described but not provided. Codex's additional `SHA256SUMS.txt`, `FINALIZATION.json`, and the rest of the reported 23-entry package were also not provided. Do not claim these unsupplied artifacts were independently checked.
4. **Claim scope:** the experiments exercise functional directed graphs without self-loops under stated constraints, not a formal proof assistant, LeetCode judge, or an ETQ-303/E8/quantum speed advantage. Neither agent established a universal fastest implementation. `tracemalloc` is *not* process RSS.
5. **Attribution:** the earlier SOFA path-state algorithm is correct and O(n). This archive records an independent witness, a signed-state alternative and evidence; it does not claim a new complexity class.

## Verify these archived bytes offline

```sh
# From repository root; no package installation:
(cd evidence/FUNCTIONAL-GRAPH-001 && sha256sum -c SHA256SUMS.txt)

# Also validate file sizes, source pin, publication registration,
# raw-to-report concordance and witness statistics:
python3 -m unittest discover -s tests -p 'test_functional_graph_archive.py' -v
``` It is deliberately read-only. `ARCHIVE.json` contains the exact file inventory, expected byte counts and Git blob identifiers. `SHA256SUMS.txt` covers all nine uploaded/reconciled originals, not itself or generated metadata.

No executable from this archive is automatically invoked by CI; the Codex verifier is retained as audit source, not run against the host by default. No changes to canonical experiments, historical receipts, SOFA content, publishing policy, or case counts.
