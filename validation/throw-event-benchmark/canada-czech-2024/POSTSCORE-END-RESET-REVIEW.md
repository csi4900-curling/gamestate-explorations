# Postscore source review: 1903–1940 s transition cluster

This is a **development review after the frozen screen**, not an independent or exhaustive throw reference. It cannot produce precision, recall or F1. The source is the 360p full recording (`e63c9b063b5b11ad5173083dffe974d909c78e5d01312740b87bccc006402013`) and the aligned 1080p interval (`6d3f489b7b908281bca9a52eb85470d95374f65f328c13e1e6daf6cbb8bf6623`). The reviewed raw, corridor and screen artifacts have SHA-256 hashes `c12923797078edf7dca107f115177b75c893776510c766990397a0c8fbf93bca`, `8295ac26dd4735923a73a1f84d33657ce024a66ed972ef04d585071673148cf7` and `aac4a9f3c42e3bda61c40edeeceb55e66e52949e701f1931b0e9ee1913711f0f`.

The pre-inference [full](source-only-5s-sheets/sheet-02.jpg), [left](source-only-left-5s-sheets/sheet-02.jpg) and [right](source-only-right-5s-sheets/sheet-02.jpg) five-second sheets show the sequence. Additional source-frame checks used the aligned high-resolution clip at **1903.3, 1905.1, 1907.0, 1918.3, 1920.7 and 1940.0 s**, plus the full source at **1910, 1945, 1950, 1965 and 1968.1 s**. To reproduce a high-resolution frame, seek `source-1080p-1650-2760.mp4` to `source_time_s - 1650` seconds.

| Raw ID | Passage time (s) | Frozen outcome | Source-visible context |
| --- | ---: | --- | --- |
| S04 | 1903.283 | No supported receiving path | Players move down the left view while a staff member collects stones around the house. |
| S05 | 1905.087 | No supported receiving path | Same clearing activity; an athlete's white jersey with red lettering passes through the apparent red-motion area. |
| S06 | 1906.982 | No supported receiving path | Same clearing activity; no source-visible new delivery in the checked frames. |
| S07 | 1918.267 | Withheld outside corridor | Players and implements cross the left view during reset; a red stone is stationary near the far house approach in the sampled frames. |
| S08 | 1920.637 | Withheld outside corridor | Same reset, with a stationary red stone and moving people. |
| S09 | 1940.022 | Withheld outside corridor | Players reposition and stones are handled as the next end is prepared. |

The right-camera scoreboard changes Czechia's total from **1** in the 1920.7 s frame to **2** in the pre-inference 1925 s sheet, corroborating an end transition in this interval. This scoreboard observation does not establish a precise end boundary or a shot timestamp. The next retained S10 cue at 1968.083 s occurs after this reset; the right-view sheet shows a red stone in transit by 1975 s.

An unchanged [broadcast end-marker scan](end-marker-full-postscore.json) of the full 360p source gives complementary context: the last sampled **end 2** marker is at 1940 s and the first sampled **end 3** marker is at 1970 s. The [candidate alignment](end-display-context-postscore.json) brackets 22 of 24 raw candidates within one displayed end and leaves S09 and S10 across this graphic change. A displayed-end transition can lag physical play; these sample times are not a physical end boundary.

**Finding:** the frozen screen prevented this six-candidate transition cluster from becoming provisional throws. The source review gives a concrete negative context—moving people and stone clearing—that a future learned or rule-based end-reset detector should recognize. It does not prove all six candidates are false in an independently scored sense, and it must not be used to retune or retrospectively rescore this frozen transfer.
