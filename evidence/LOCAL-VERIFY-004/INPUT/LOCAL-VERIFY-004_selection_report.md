# LOCAL-VERIFY-004 — Public YouTube candidate selection

Eight videos inspected; **seven explicitly list English (auto-generated) captions, and one is a provisional negative**. This is browser reconnaissance for QSOL-IMC / HERESY-SOFA. Actual yt-dlp metadata extraction and subtitle downloading remain **NOT_TESTED** and require the separately authorised execution.

Source: [Trent Slade — Videos](https://www.youtube.com/@trentslade83/videos). The public channel displayed 235 videos. This purposive sample came from the initial Latest listing; it is not a channel census. Signed-out Cloud Browser, English interface, AU locale marker. Recorded candidate observations: **6 November 2026, 20:44:30–20:48:22 Australia/Adelaide** (10:14:30–10:18:22 UTC). Per-video timestamps are in the JSON.

## Five recommended candidates

| Rank | Exact title and verified watch URL | Video ID | Displayed publication date | Duration | Caption-menu observation | Proposed test |
|---|---|---|---|---|---|---|
| 1 | [Inside the Bureau of Software Anomalies \| HERESY-SOFA](https://www.youtube.com/watch?v=dKp50fVKUtw) | `dKp50fVKUtw` | 2026-11-02 | 19:03 | English (auto-generated) | Positive baseline directly tied to the project |
| 2 | [No Prayer In The Wire](https://www.youtube.com/watch?v=-425IRSpUNc) | `-425IRSpUNc` | 2026-10-30 | 4:11 | English (auto-generated) | Shortest inspected positive; contrast with the negative candidate |
| 3 | [CorpoWars OST - No Shareholders Were Consulted](https://www.youtube.com/watch?v=eki6bbbZ7AI) | `eki6bbbZ7AI` | 2026-11-03 | 4:40 | No Subtitles/CC entry in opened Settings menu | Provisional negative; extraction must establish whether tracks are actually absent |
| 4 | [VanillaJS \| Optimized Engine For creating Offline Web Browser Games using Web Standards.](https://www.youtube.com/watch?v=p2zo4fuOhgM) | `p2zo4fuOhgM` | 2026-11-06 | 12:06 | English (auto-generated) | Recent-release positive; check for caption-state changes at execution |
| 5 | [Offline AI Transcription with M4A2TXT v0.4.0 Release: CUDA Engine Fixes & Progress Bars](https://www.youtube.com/watch?v=bGSY2mbC1XI) | `bGSY2mbC1XI` | 2026-11-04 | 20:10 | English (auto-generated) | Longer positive, adding duration variation |

These provide four proposed positives and one provisional negative, spanning 4:11–20:10 and displayed dates from 30 October to 6 November. Selection uses observed menu evidence, project relevance and duration/date variation. No caption classification was inferred from a title or music genre.

## Reserve candidates

| Exact title | Video ID | Displayed date | Duration | Caption-menu observation |
|---|---|---|---|---|
| [Three Faces At The Kill Switch](https://www.youtube.com/watch?v=URO2P5jRGQo) | `URO2P5jRGQo` | 2026-10-30 | 4:29 | English (auto-generated) |
| [AudioPod Converts Text to AudioBooks with Offline AI](https://www.youtube.com/watch?v=XzLSwYIdhns) | `XzLSwYIdhns` | 2026-11-05 | 20:46 | English (auto-generated) |
| [Is the Sky ACTUALLY Black? [The Science of Atmospheric Gaslighting]](https://www.youtube.com/watch?v=2yxWX2rcAdw) | `2yxWX2rcAdw` | 2026-10-30 | 14:22 | English (auto-generated) |

The first two overlap selected short/long positive cases. The atmospheric experiment is an alternative with visible chapter navigation and a different subject.

## Evidence boundaries

- **Conflicting UI signal:** all seven positive candidates had a CC accessibility label saying “Subtitles/closed captions unavailable” while their opened Settings/subtitle menus explicitly listed **English (auto-generated)**. Classify them as menu-listed positives and preserve the discrepancy. The CC button alone is not a reliable negative oracle in this browser.
- Each positive submenu showed **Off**, **English (auto-generated)** and **Auto-translate**. No other native language was listed. Auto-translate was not opened or counted as a supplied track; its target-language list is **NOT_TESTED**.
- The provisional negative showed a CC-unavailable label, no Subtitles/CC entry in Settings, and no Show transcript control in the expanded-description snapshot. This is a single-client observation, not proof of permanent or global track absence. Caption origin and language are **unknown / NOT_TESTED** for this candidate.
- English is the explicitly labelled caption language for the seven positives. Actual spoken/sung language and uploader-declared original language are **NOT_TESTED**. English titles/descriptions do not establish audio language.
- Dates are copied from expanded descriptions/Video details; publication instant and timezone are **NOT_TESTED**. Durations come from player totals. IDs come from observed watch URLs, with channel attribution checked on the pages.
- Manual-caption confirmation, multiple native caption languages, extractor keys/formats/URLs, caption accuracy/completeness/timing, subtitle retrieval and downloaded-content verification are **NOT_TESTED**. No execution pass is claimed.
- No media-file downloads or exports were performed. Watch pages may buffer automatically; autoplay was paused when exposed. No channel settings were changed, no YouTube uploads occurred, and nothing was published to SOFA.
- JSON contains compact transcribed browser evidence and per-candidate limitations. No screenshot archive or complete raw DOM capture is attached. It is an observation inventory, not yt-dlp output; an extracted-metadata hash is **NOT_TESTED**.

## Separate execution boundary

For a later authorised LOCAL-VERIFY-004 run, pin the extractor version, preserve original metadata and its SHA-256, and compare actual caption inventories against these timestamped hypotheses. A changed or contradictory result is evidence to investigate. Subtitle downloading and content validation remain separate from successful metadata extraction. No such execution was performed here.
