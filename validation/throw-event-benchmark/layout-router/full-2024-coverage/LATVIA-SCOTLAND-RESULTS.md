# Latvia and Scotland full-source routed transfer

The [pre-run plan](LATVIA-SCOTLAND-PLAN.md) fixed the existing 90-second
layout router and 2024 span/context adapter before these full-source runs.
The [machine-checked audit](latvia-scotland-full-transfer-audit.json), made by
[`audit_latvia_scotland_full_transfer.py`](../../../../prototype/scripts/audit_latvia_scotland_full_transfer.py),
verifies source hashes, preflight/timeline links, each run's raw/accepted/review
accounting, and replay of the earlier fixed 1650–2760 s raw interval. These
sources already had exposed development intervals; this is **not** an
independent physical-throw accuracy measurement.

| Full recording | Supported / requested | Explicit unknown | Raw motion proposals | Auto-accepted candidates | Review proposals | Normal completed-end deliveries |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| [Canada–Latvia](latvia24-full-v1/timeline.json) | 6,840 / 7,059 s | 219 s | 119 | 72 (36 red, 36 yellow) | 47 | 96 (48 each colour) |
| [Canada–Scotland](scotland24-full-v1/timeline.json) | 6,570 / 7,347 s | 777 s | 158 | 112 (61 red, 51 yellow) | 46 | 112 (56 each colour) |

The official [2024 results book](../../../official-shot-sequence/WWhCC2024_ResultsBook.pdf)
shows six completed Latvia–Canada ends (PDF page 51) and seven completed
Scotland–Canada ends (PDF page 54). Sixteen deliveries per completed end gives
the nominal totals in the table. This is an **order/count constraint**, not
timestamped video truth. If all nominal throws are present in each recording,
Latvia's 72 accepted candidates leave at least 24 deliveries unmatched even
in the impossible best case that every candidate is real and distinct. Its
count-limited recall ceiling is 72/96 = 0.75. Scotland's equal **total** of
112 is misleading: 61 red claims exceed the normal 56 red deliveries by five,
while only 51 yellow claims exist for 56 yellow deliveries. Under a one-to-one
colour-aware interpretation, at least five red claims are extra or wrong-colour
and at least five yellow deliveries lack a yellow-labelled candidate. Counts
cannot say which events are wrong; event-only precision/recall and F1 remain
unmeasured.

The [Latvia gap sheet](latvia24-full-v1/gap-contact.jpg) samples the title
sequence and final scoreboard/credits around the two unknown spans, 0–90 and
6930–7059 s. The [Scotland gap sheet](scotland24-full-v1/gap-contact.jpg)
samples all eight unknown spans. Its six 90-second **interior** gaps (2070–2160,
2250–2340, 3870–3960, 4500–4590, 6120–6210, 7020–7110 s) all show the
split-screen match view in the sampled source frames, with players or stones
on the ice. The router reported only 4–6 split-signature samples out of nine
in those chunks. These sparse stills do not prove a throw occurred in any
particular gap, but they show the unknown designation can interrupt live-match
coverage. Ten Scotland candidates are also within 40 s of a supported-run
boundary and need separate boundary review. The contact sheets and manifests
were rendered from source frames by
[`render_layout_gap_contact.py`](../../../../prototype/scripts/render_layout_gap_contact.py).

The full Latvia raw pass exactly reproduces all 27 earlier same-colour passage
times inside the fixed interval. Scotland reproduces all 27 comparable earlier
passages and adds one red passage at 2759.737 s, only 0.263 s before the old
interval ended; the longer run gives that track time to be emitted. Thus the
full-source count differences are not explained by a drifting detector version
inside the exposed interval. This checks raw-passage reproducibility only; the
earlier fixed-grid motion/stone-patch screen is a different downstream filter.

The result puts two concrete requirements on the next detector iteration:
route split-screen live play without discarding Scotland's interior chunks,
and validate the resulting physical throw/colour sequence against a source-first
complete-match reference. The current routed timelines remain partial
candidate observations, not final throw segmentation or game-state input.

An unchanged 2024 scoreboard-marker reader was also tried on both full
recordings. Its [source-checked transfer audit](MARKER-TRANSFER-FAILURE.md)
found zero Latvia markers and a one-column Scotland end-number error despite
high image similarity. Its output is **not** used to assign candidates to
ends or to repair the event counts above. A separate
[2D-registered development scan](2D-MARKER-CANDIDATE-CONTEXT.md) now attaches
repeated *displayed*-end context to most accepted candidates while retaining
unknown physical end and throw identity.

A later [source-activity audit](ACTIVE-STATIC-LEFT-RESULTS.md) explains a major
part of Latvia's coverage failure: for 1655 seconds inside the supported run,
the left panel is visually static while the right panel changes. The left
trigger emits no raw candidate there. This does not count missed physical
throws, but it invalidates the router's supported-delivery-camera assumption
over that span.
