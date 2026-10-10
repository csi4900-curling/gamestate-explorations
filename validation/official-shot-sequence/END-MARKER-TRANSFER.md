# 2024 broadcast end-marker transfer probe

The [reader](../../prototype/scoreboard_end_marker.py) finds the active-end
chevron in the 2024 WWhCC broadcast graphic. A clear Canada–China frame at
500 s supplied its binary chevron shape. For each recording, the
[scanner](../../prototype/scripts/scan_2024_end_markers.py) estimates the
graphic's horizontal shift from paired red/yellow team panels and the end
column width from repeated header edges. It samples the video every 10 s and
abstains on absent, covered or ambiguous graphics. The three frozen
[raw scans](end-marker-china-geometry-10s.json),
[Estonia scan](end-marker-estonia-geometry-10s.json), and
[Italy scan](end-marker-italy-geometry-10s.json) contain source hashes,
calibration observations, every sampled read and raw marker changes.

| Recording | Panel shift | Column pitch | Confident reads / samples | Repeated end numbers | Isolated backward reads |
| --- | ---: | ---: | ---: | --- | ---: |
| Canada–China | 0 px | 9.7 px | 427 / 818 | 1–8 | 0 |
| Canada–Estonia | 20 px | 9.6 px | 400 / 844 | 1–8 | 2 |
| Canada–Italy | 28 px | 9.4 px | 323 / 834 | 1–8 | 1 |

The [temporal summary](end-marker-temporal-summary-v1.json) retains only runs
with at least two reads. This removes the isolated Estonia readings at 2330
and 8020 s and the isolated Italy reading at 6430 s from its **stable** change
list, while leaving all raw reads in the scan files. It never inserts an end
missing from the graphic. Italy's displayed end-8 marker has only three
confident reads; the official score sheet marks that end `X`, so the marker
alone does not establish that end 8 was played.

The chevron is a *broadcast display state*, not a physical end boundary. In
China, its seven transition intervals occur 1–137 s after the corresponding
source-reviewed end-change frames when compared by midpoint. The graphic
can still show the previous end after the next end's first delivery. Using
the marker transition as a cutpoint would misassign real throws. The reader
therefore supplies sequence context and candidate boundary windows only;
the end-aware candidate audit still uses source-reviewed physical boundaries.

The layout and matching choices were developed while inspecting all three
recordings. This is a reproducible development transfer check, **not an
independent validation set or throw-event F1 result**. Other tournament
graphics require recognition or abstention before their end markers can be
used. The source [layout snapshots](scoreboard-layout-china.jpg),
[Estonia](scoreboard-layout-estonia.jpg), and
[Italy](scoreboard-layout-italy.jpg) show why a fixed x coordinate fails.

The [display-context aligner](../../prototype/end_display_context.py) attaches
an end number to a provisional throw **only** when readings within 30 s on
both sides agree. It records `physical_end: null` in every output. The frozen
[China](end-display-alignment-china-v1.json),
[Estonia](end-display-alignment-estonia-v1.json), and
[Italy](end-display-alignment-italy-v1.json) ledgers have respectively 82/131,
59/128 and 43/109 candidates with locally bracketed display-end evidence;
48, 68 and 63 remain unknown, and 1, 1 and 3 span displayed changes. China
R01-S64 at 1939.75 s is source-reviewed as an end-3 candidate while the
bracketing graphic still says end 2. The aligner leaves that disagreement
visible, demonstrating why even a confident displayed end cannot be treated
as the event's physical end.
