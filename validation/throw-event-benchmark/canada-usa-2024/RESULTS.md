# Canada–USA 2024: frozen first span-context transfer

**Meeting-ready version:** [read the illustrated French report](RESULTS.html).
This file preserves the concise technical record and artifact names.

The interval, source-only reference and detector/scorer hashes were fixed in
`SELECTION.md` before candidate inference. The unmodified pipeline processed
1650–2760 s of source `Z1yEOv__bDc`. The reference has 20 coarse delivery
windows prepared from source-only still sheets by the developing agent.

| Scoring contract | TP | FP | FN | Precision | Recall | F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Frozen first score, zero tolerance | 19 | 1 | 1 | 0.950 | 0.950 | 0.950 |
| Post-score sensitivity, one-second tolerance | 20 | 0 | 0 | 1.000 | 1.000 | 1.000 |

There were no colour errors among matches. The first score is the result to
retain for transfer measurement. Its only mismatch is one yellow passage,
`S24`, at 2344.448 s versus source-only reference `U14`, whose coarse interval
starts at 2345 s. Source frames at 2339–2350 s show the corresponding yellow
delivery; the detector event is 0.552 s before the labelled window. The
one-second score is a **post-score boundary sensitivity check**, not a revised
held-out score or new independent evidence.

The detector emitted 39 motion-span candidates and confirmed 20; 19 were
withheld with recorded reasons. The confirmed time is the midpoint of an
observed early-view track, not release time. This is an 18.5-minute interval
from a single 2024 production family, not a complete match. Five-second
source sheets outside one denser changeover may miss a brief delivery, and
the reference was made by the same agent developing the detector. Thus the
first score supports a promising same-family transfer, but does not establish
the full-recording, cross-family high-F1 target or physical throw boundaries.

Immutable first-pass artifacts: `blind-reference.json`, `frozen-first-raw.json`,
`frozen-first-motion.json`, `frozen-first-confirmed.json`, and
`frozen-first-score.json`. `audit-u14.png` and
`postscore-one-second-tolerance.json` were created only after the first score.
