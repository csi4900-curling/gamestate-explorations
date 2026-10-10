# Full Slovakia–USA 2022 frozen transfer result

The [transfer plan](TRANSFER-PLAN.md) fixed the China-developed rules and
the shot-origin model trained without Slovakia labels before inspecting
this full-match inference. The source is the exposed 0–7616 s
Slovakia–USA 2022 recording, not the reserved independent video.
`run_full_shot_evidence.py` produced and rechecked all 19 stages without
manual labels. Its 5 Hz cut scan found 495 broadcast shots, and the cuts
inside the previously reviewed 2400–2700 s interval exactly reproduce
the earlier scan. Sixteen of 18 shot intervals match that earlier review;
their frozen probabilities match except for the last shot, whose
following-shot context changes at the interval boundary.

| Evidence | China full-match development | Slovakia frozen transfer |
| --- | ---: | ---: |
| Source seconds / broadcast shots | 8,356 / 630 | 7,616 / 495 |
| Readable counter seconds | 5,574 | 4,517 |
| Replayed counter updates | 116 | 98 |
| Frozen view proposals | 129 | 115 |
| Counter updates associated by cap motion | 92 | 88 |
| After selected learned-box motion | 100 | 89 |
| After immediate-following-motion route | 112 | 92 |
| After existing-visual conflict link | 115 | 94 |
| Travel-only counter candidates | 1 | 0 |
| Final provisional candidate records | 130 | 119 |
| Visual-only candidates without counter link | 14 | 25 |
| Counter/visual colour conflicts | 9 | 3 |
| Counter-state discontinuities | 12 | 18 |

The Slovakia counter replay changed none of the 98 raw updates. The
counter was unreadable for 3,099 seconds and had 48 unresolved changes.
The learned-box stage scanned 88 selected shots (8,218 frames), rather
than the entire source. The final [candidate ledger](candidate-event-ledger.json)
links 94 counter updates to visual candidates and leaves four unlinked.
B80 (red, 5832 s) and B86 (red, 6421 s) each have competing plausible
motion-supported shots, so the frozen association rule abstains. B88
(yellow, 6458 s) and B92 (yellow, 6670 s) lack the required motion
support. None qualified for the travel-only fallback. A permissive
one-to-one temporal match can pair 97/98 counter updates with some
candidate, which illustrates why timing alone is weaker than event
identity and colour evidence.

This transfer shows meaningful counter concordance across a second full
recording, but it does **not** show 0.95 throw-event precision, recall
or F1. The counter is incomplete and delayed, and 25 visual-only
candidates could include both real throws during hidden-counter spans
and false positives. The four unlinked updates and 18 state breaks are
explicit failures/uncertainties for the next detector and game-state
work. No release-time, settled-board or physical-trajectory validation
was performed.

## Preselected source-only event review

The [review plan](SOURCE-REVIEW-PLAN.md) selected three 300-second windows
from the source hash before inspecting interval predictions. The
implementing agent reviewed five-second full-frame contact sheets and
froze [13 clear delivery windows](source-only-event-windows.json), with
two uncertain boundary cases excluded. The
[one-to-one temporal score](source-only-event-score.json) found 13/13
clear events overlapped by an eligible candidate release window, with
one extra candidate: precision 13/14 (0.929), recall 13/13 (1.000),
F1 0.963. The extra is T087 near the first sixth-end yellow delivery.
Two temporal matches have a conflicting predicted colour (T035 and
T086), and two have unknown colour (T085 and T117). With colour required,
the same overlap rule yields 9 true matches, 5 extra candidates and 4
missed event identities (precision 0.643, recall 0.692, F1 0.667).
T087 is a delayed yellow counter-backed candidate near the same real
yellow delivery that T086 matches temporally as red. Thus the unmatched
T087 row is likely a duplicate/late association rather than proof of
an additional physical throw.

This is a **development diagnostic**, not an independent or exhaustive
match-level F1 estimate. The agent who built the detector also authored
the source review; five-second sampling may miss off-camera throws; and
broad candidate windows can yield temporal matches without accurate
release times. The colour conflicts and extra candidate are concrete
issues to resolve before game-state reconstruction.

## Postscore identity audit

The [separate identity audit](identity-ambiguity-audit-v2.json) preserves
the frozen event ledger. It flags three visual-only red candidates whose
shot has no red learned-stone track while the next shot contains earlier
yellow motion: T035, T086 and T110. The first two were already wrong-
colour matches in the preselected source review. A targeted source-only
[follow-up](risk-followup-6615/sheet-01.jpg) shows a yellow delivery at
T110 as well. The audit also records a plausible delayed-counter link
from T086 to yellow counter candidate T087; it does not merge them.

An exploratory earliest-following-motion rule proposes 12 alternative
colours on this match. A separate targeted [source check](hypothesis-followup-1240/sheet-01.jpg)
supports yellow rather than ledger red at T021, but these model-selected
checks are retrospective. The rule remains a hypothesis until a frozen
cross-recording check; it is not used to rewrite the original ledger.
Applied retrospectively to the preselected 13-event review, the
[versioned colour hypothesis](source-only-colour-hypothesis-score.json)
raises colour-aware F1 from 0.667 to 0.963 by assigning yellow to all
four wrong/unknown matched colours. This is **development fitting after
source inspection**, so the improved number cannot establish transfer
accuracy. The baseline ledger and original first score remain preserved.
