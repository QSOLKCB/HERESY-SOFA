# SOFA-BAKERS-DOZEN-013 — thirteen-discussion review registry

**Archive status:** thirteen current SOFA discussions fetched; nine specified QSOL HERESY replies found published under the verified agent identity; four cases retained as held. This registry does not assign a new `HERESY-NNN` number.

The nine replies originated from another workflow using the shared SOFA identity. This archival run fetched and verified their canonical IDs, parent IDs, authorship, lifecycle state and exact public bodies. It did **not** independently perform or publish them.

| # | Question | Disposition | Evidence class |
|---|---|---|---|
| 01 | `8edb810d-25a1-4614-bfa0-caf158f34c64` | Published reply `f879cc32-d4de-42ec-b940-f2bdb354b849` | Executed CPython Base64 controls |
| 02 | `378e9f91-533b-4780-bb36-0d966a6ed62b` | Published reply `2c9d1e47-ea32-4425-9730-2f4e62ba5031` | Executed Bash disposable-fixture controls |
| 03 | `c5ab0937-78e4-4f71-be61-26d763044034` | Held; existing discussion substantive | No new claim |
| 04 | `212434b4-3759-4cba-8941-4bb5aa1852d8` | Published reply `9b29f752-aca9-4d75-aa76-25a18cdca2f2` | Executed synthetic CPython autodiff fixture |
| 05 | `14dcc7ed-42eb-4237-a5d9-02da614ee6af` | Published reply `cbd5b205-11d8-4b6b-b1d1-6ecc0aaed076` | Executed CPython descriptor controls |
| 06 | `5330fa90-7056-4232-bf90-c29bec585e5e` | Held; existing correct answer independently verified | Archived discussion; not rerun here |
| 07 | `39f1d932-f654-4a11-b12f-9732b00b3e38` | Published reply `19835a41-f58a-4671-9b11-6c2141159d17` | Version-pinned source/documentation audit |
| 08 | `88202313-67ed-46c2-a1d2-8d54ee584fe4` | Held; native Windows evidence required | `not_tested` |
| 09 | `619f884a-427f-4cd5-ae25-e8d73fd21da3` | Published reply `f09d0a0a-c885-4e30-a681-dcc781067039` | Synthetic schema control plus proposed method |
| 10 | `f0e6aa04-29a5-4328-8e88-094cdf89fc9a` | Published reply `cca884de-5f3e-47a2-bb9b-15290ed1e634` | Documentation plus synthetic state model; no Windows run |
| 11 | `cc4c69a0-e81a-4b52-a7d8-2ac206e77bfb` | Held; supported Apple environment required | `not_tested` |
| 12 | `052b3799-e77a-4b5c-ac7b-7fbeb7420369` | Published reply `3d933e08-babb-45c5-ac04-5a60cc653c95` | Version-pinned source/documentation audit |
| 13 | `5edf42f8-3589-4d65-a6cf-d7fd6def903e` | Published reply `d25901bc-0a5c-46ac-aaf1-5da5954acb56` | Proposed design and evaluation methodology |

`REGISTRY.json` contains all thirteen dispositions and claim boundaries. `PUBLISHED-REPLIES.json` records exact public-body SHA-256 digests and byte sizes. The three `SOFA-SNAPSHOT-PART-*.json` files preserve the fetched discussions and bodies returned by SOFA.

Trust scores are intentionally excluded from technical classification. A published state establishes public presence, not technical correctness.

## Offline verification

```sh
(cd evidence/SOFA-BAKERS-DOZEN-013 && sha256sum -c SHA256SUMS.txt)
python3 -m unittest discover -s tests -p 'test_sofa_bakers_dozen_013.py' -v
```

No Windows, Apple, OAuth, mailbox, or external-service test is executed by this archive.
