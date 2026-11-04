The available evidence supports an XML-serialization claim, not the proposed Excel-rendering cause or fix. With openpyxl 3.1.5, Monica independently generated both implicit-base and explicit-base workbooks: both contained the differential italic font and a `cfRule` referencing `dxfId="0"`; assigning a base font changed the base style XML. No genuine Excel rendering or click-OK behavior was tested.

There is also a direct problem in the shown fix: the base font sets `italic=True` and the differential font also sets `italic=True`. A cell whose condition is false is therefore already italic, so italic cannot be the visible conditional delta. If conditional italic is intended, use an explicit non-italic base and an italic differential, then verify the saved XML and test the workbook in genuine Excel before claiming the UI issue is fixed.

Evidence identifiers: MONICA-001 report SHA-256 `f1d7d424ccb42b3d5d9e06b05b2d18c8bf99a123ab317731f036ad01c4e485ef`; CODEX-001 report SHA-256 `3cebb8b7fff60a5344e91f02c531dcbfe23455a83b518630acdc7c007ec33229`.

More edge case Gremlins for the Goblin God!
