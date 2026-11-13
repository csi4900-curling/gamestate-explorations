# Italy full-match blind-view runner transfer

The [saved 360p source](../../../../../source-cache/Vp3TIdOAlrc-360p.mp4)
matches the frozen Italy timeline source hash. The current source-activity
audit and coverage overlay reproduce the existing **2835–3200 s**
active-right/static-left interval: 365 newly unsupported seconds, 7735
supported seconds and 605 unknown seconds across the 8340-second source.

The unchanged 1 Hz right-view probe again finds **nine raw moving-colour
tracks** in that interval. The unchanged early-entry triage selects **zero**
right-only review entries; the new camera-aware fusion therefore has zero
rows. This reproduces the earlier source-activity, right-motion and entry
triage results exactly at their recorded intervals and track times. It does
not establish that the interval contains no deliveries: a true stone could
miss the colour, motion or entry rule.

The old Italy runs have saved `raw.json` and `events.json` but no `triage.json`.
The current [candidate union](italy-candidate-review-union-current.json)
reconstructs the lossless triage from those saved artifacts and records their
hashes and the current triage-code hash. It contains **157 left proposals**:
109 context-confirmed and 48 withheld, with no right-only addition. The
[candidate-to-state handoff](italy-candidate-state-handoff-current.json)
marks all 157 as unsampled by this right-only board stage and keeps complete
game state and simulation readiness unknown. All 157 left rows carry their
source-observed motion span, with a median length of **1.2 s**; those short
spans are candidate evidence, not complete throw segments. No throw precision,
recall, F1 or physical board accuracy follows from this development transfer.
The [adjacent-board sequence](italy-right-board-sequence-current.json) also
produces zero comparisons, as expected from zero right-only entries. This is
an empty comparison, not evidence of unchanged physical game state.
The [left-candidate scan](italy-left-partial-caps-current.json) covers all 157
left proposals: 71 partial stable cap sets, 20 with no stable caps, and 66
abstentions (23 time-bracket disagreement, 11 scene/player motion, 32 next
candidate/route boundary). The [v2 handoff](italy-candidate-state-handoff-v2.json)
attaches these observations without asserting complete boards. A four-frame
source inspection found marked cap proposals on visible stones, while other
visible stones were missed; the output remains an incomplete image sample.
The [adjacent image-board sequence](italy-candidate-image-board-sequence-current.json)
checks all 156 pairs. It permits 24 conditional comparisons (20 locally
matched cap pairs), abstains for 116 missing usable cap sets and 16
painted-house alignment failures. These image associations do not prove
physical stone transitions or complete post-throw states.
The [image-house ellipse export](italy-candidate-house-ellipse-current.json)
retains a stable three-frame painted-house ellipse for **48 of 71** usable cap
observations (11 geometry-change and 12 missing-ellipse abstentions). It
normalizes 55 cap pixels to the fitted image ellipse, without claiming rink
metres or a complete board. The contour thresholds were adjusted after
inspecting Latvia and Italy, so these are exposed development results.
