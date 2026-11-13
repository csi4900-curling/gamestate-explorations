# Raw scoreboard readings around emitted counter updates

The [reproducible audit](pwg2022-counter-sample-support-development.json) retains visible one-second scoreboard readings 2–12 seconds before and after every *raw* emitted counter update in four exposed 2022 recordings. It reports the fraction matching each update's recorded before and after count, with no accept/reject threshold.

| Recording | Raw emitted updates | Both contexts visible | Both exact-state fractions ≥0.75 |
| --- | ---: | ---: | ---: |
| Switzerland | 103 | 96 | 14 |
| China | 119 | 112 | 19 |
| Slovakia | 98 | 95 | 12 |
| Canada–Norway | 100 | 97 | 13 |
| **Total** | **420** | **400** | **58** |

Only 58 of 400 updates with readings on both sides meet a naive 0.75 exact-state criterion. A hard gate at that value would discard many emitted counter observations; this does **not** measure physical throw recall, because the emitted updates themselves are not independent throw labels. The one-second colour-slot reader often alternates between adjacent counts. The existing counter state machine already waits for repeated readings, but its emitted update time can still be broad or uncertain.

Slovakia B80 illustrates the local ambiguity: its 5832 s update has 4/6 preceding visible reads matching `[4,2]` and 3/7 following reads matching `[3,2]`; the other reads are adjacent states. B81 at 5860 s has 5/11 matching `[3,2]` before and 3/4 matching `[2,2]` after. The raw counts repeatedly alternate around the two updates, so the visual red passage in S374 cannot be assigned to one of them from the graphic alone.

The China raw audit has 119 emitted events, while its later replay used elsewhere in the project has a different count. This table describes raw audits only; counter IDs should not be joined across those versions without an explicit mapping. The report does not alter the counter extractor, event ledger, or any measured F1. Reproduce with `python prototype/scripts/audit_2022_counter_sample_support.py`.
