# Sweden–Switzerland 2022 full-match development transfer

The [pre-run plan](TRANSFER-PLAN.md) fixed the 19-stage pipeline, a
Swiss-excluding shot-origin model and the experimental colour-audit rule.
The source is the exposed 0–7734-second Swiss recording. Earlier Swiss
development labels exist, so this is a cross-match **development** check,
not independent full-recording validation. All original event candidates
are in the [unchanged ledger](candidate-event-ledger.json).

| Full-recording evidence | Result |
| --- | ---: |
| Broadcast shots / frozen origin proposals | 604 / 142 |
| Counter-readable seconds / stable updates | 4,952 / 103 |
| Counter updates linked after cap motion | 93 |
| After selected learned motion | 92 |
| After following-motion rescue and visual link | 97 |
| Travel-only counter candidates | 2 |
| Final provisional candidates | 121 |
| Counter-backed / visual-only candidates | 99 / 22 |
| Unlinked counter updates / counter-state breaks | 4 / 16 |

The selected learned-motion stage scanned 93 shots and 6,935 frames.
Four counter updates remain unlinked: B15, B71, B74 and B87. The
[identity audit](identity-ambiguity-audit.json) flags two visual-only
colour-collision risks and records 12 alternative earliest-following-
motion colours across the full match. It is evidence for investigation,
not a rule that merges candidates or confirms throws.

Before inspecting the full-match candidate rows in the sampled spans,
the implementing agent froze [15 coarse source-only delivery windows](source-only-event-windows.json)
across three video-hash-selected 300-second intervals. After removing
uncertain boundary spans, the [one-to-one overlap score](source-only-event-score.json)
finds 15 temporally matched candidates, zero unmatched candidates and
zero missed coarse windows. Temporal development precision, recall and
F1 are all 1.00 **on those windows**. One matched candidate has unknown
colour, so colour-aware precision and recall are 14/15 (0.933), F1 0.933.
The frozen [colour-hypothesis variant](source-only-colour-hypothesis-score.json)
assigns red to that one candidate, raising colour-aware F1 to 1.00 on
the same sampled windows. Eleven other colour alternatives fall outside
them, so this check provides little evidence about the rule's general
colour precision.

The first diagnostic scorer incorrectly selected candidates by shot
start time and excluded one red candidate that began 2.6 seconds inside
an uncertain edge but extended into a clear reviewed delivery. The
[first baseline score](source-only-event-score-anchor-v1.json) and
[first variant score](source-only-colour-hypothesis-score-anchor-v1.json)
are preserved. The corrected scorer selects candidates whose release
windows overlap an evaluable sampled span; it leaves the detector and
review labels unchanged. The Slovakia sampled score is unchanged by
this correction.

These scores use broad release windows and five-second source samples
reviewed by the implementing agent. They do not measure exact release
time, independent full-match throw F1, identity in the 22 unlinked
visual candidates, settled boards or trajectories. The 0.95 precision
and recall gate on complete independently labelled recordings remains
open.
