# Broadcast-shot origin and adjacent-motion development study

The event detector needs evidence that a new stone left the delivery side.
An isolated stone patch or a long image-space track can instead be an old
house stone, player, wheelchair, graphic, or camera pan. This study uses
hard cuts to define broadcast shots, a three-frame current/following-shot
origin classifier, and same-colour cap/learned-box motion across the cut.
Every output is still a **candidate**, not a confirmed physical throw.

The 300-second China (300–600), Slovakia (2400–2700), and Swiss
(3900–4200) intervals supplied 58 retrospectively labelled shots. A
single-shot spatial colour/ice model transferred poorly to the Swiss
end break (0 TP, 8 FP, 1 FN there). Following-shot context plus a live-overlay
condition was fitted after that failure and retrospectively classified all
58 labels correctly across leave-one-match-out folds. That perfect score is
postscore development fitting, not independent validation.

| Subsequent Swiss interval | Frozen shot-origin TP/FP/FN | Frozen two-shot TP/FP/FN | Weak-origin rescue TP/FP/FN | Unresolved labels |
| --- | ---: | ---: | ---: | ---: |
| 1200–1500 s, live | 6/3/0 | 6/0/0* | not applied | 2 |
| 3300–3600 s, live | 4/4/1 | 4/0/1 | 5/0/0* | 1 |
| 1800–2100 s, live and graphic interruption | 4/0/1 | 4/0/1 | 4/0/1 | 3 |

An asterisk marks a **postscore** rule fitted after seeing that interval's
errors. The 3300–3600 two-shot score and 1800–2100 rescue score were frozen
before their respective source-only labels were compared with predictions.
All labels are agent-authored, from three sampled frames per shot in the
same exposed Swiss source match. These scores measure shot-origin decisions
on resolved reviewed shots, **not** full-video throw-event precision,
recall, F1, exact release timing, or game-state accuracy.

The held-out transfer failures have different causes:

- At 1200–1500 s, the view model gave three player closeups high origin
  probability. None had sustained same-colour cap motion in both the current
  and following shot. The two-shot check removed them, but that rule was
  selected after this first score.
- At 3300–3600 s, the view model missed a real red throwing-side shot at
  S25 (probability 0.259). Both cap and learned-box channels carried red
  motion across the cut. A development rescue requiring both channels to
  agree and probability ≥0.2 recovered it on the exposed interval.
- At 1800–2100 s, the frozen rescue still missed the red delivery at S28:
  origin probability 0.003, despite red motion in both channels and a later
  red counter decrement. Thus the current view model's low score cannot be
  treated as reliable negative evidence. Some cap/box tracks also support
  both colours, so two-shot motion alone cannot assign the delivered colour.

Each interval directory contains its preselection, cut scan, source-only
shot sheets and labels, frozen first predictions, cut-separated cap/box
tracks, transition audits and first decision scores. The source sheets and
labels were written before their corresponding model predictions. All
artifacts record hashes and first scores are immutable. The reserved unseen
recording was not used.

The next detector revision should represent live phase, delivery-side
action, outgoing-stone motion and counter changes as separate evidence,
then associate one event with a stone across shots. A low view-classifier
score needs an explicit uncertain state when the other evidence supports a
delivery. Evaluation still needs exhaustive independent full-recording
labels to establish the 0.95 precision and 0.95 recall target.

## Delayed-counter association probe

A postscore development audit now treats each stable broadcast counter
decrement as delayed, colour-specific evidence. It searches nearby live
shots for same-colour motion in both that shot and the next shot, ranks
plausible shots by the existing origin probability, and abstains if the
best two are too close. It does not read the shot labels when associating.

Across five exposed 300-second intervals with counter audits, this
associated **24 of 25** stable decrements. All 24 chosen shots have
agent-authored positive shot-origin labels; the unmatched decrement is
at the left edge of Swiss 3300–3600, where the delivery may precede the
interval. The Swiss 1800–2100 red shot that the frozen detector missed
was recovered as a counter association despite its origin probability
of 0.0027. Per-interval evidence is in `counter-shot-alignment.json`.

This result measures the purity of a selected set of **weak positive
training examples**, not full-video detector precision or recall. There
are missed or unreadable counter changes, possible shot-cut errors,
and no independent labels. These associations should be expanded to
more source footage, then used for training only; a separate complete,
independently labelled recording is still needed for F1 measurement.

## Shot-level evidence fusion

The development fusion stage retains three separate routes: a strong
origin view corroborated by adjacent motion; a weak origin supported by
both motion channels; and a delayed counter change associated with
same-colour adjacent motion. The counter route recovers Swiss S28 even
though its origin score is near zero. The dual-motion route recovers
Swiss S25 in a section with no stable matching counter decrement.
Counter/visual colour disagreement becomes an explicit conflict, and
an unmatched counter event stays unresolved. The output bounds a
delivery-looking broadcast shot; it does not claim exact release or
full stone trajectory.

On the five exposed intervals, fusion selects 29 candidate shots for
29 resolved agent-positive shot labels, with zero labelled false
positives or false negatives. Four selected candidates have unresolved
colour. The per-interval `fused-shot-candidates.json` files include
source hashes, evidence provenance and scores. **This 29/0/0 is
postscore development performance**, partly using rules chosen after
earlier misses; it is not an independent event-level F1 or proof of
cross-recording reliability. The next useful scale test is an entire
non-reserved recording with all shots and counter-visibility gaps
included, followed by the separate independent recording gate.

## Full-recording development scale test

The [Canada–China 2022 full-match run](china-full-transfer/README.md)
now covers 8,356 seconds and 630 broadcast shots without requiring a
label file for frozen model inference. The original counter audit has
119 changes, and its preserved postscore replay removes three graphic
duplicates. Against the replayed 116 updates, per-shot cap motion
associates 92 with shots; selected learned boxes raise this to 100;
postscore immediate-following-shot rescue raises it to 112. The final
fusion retains 129 candidate shot windows, six with unknown colour
because counter and visual colour evidence conflict. A permissive
one-to-one temporal proxy pairs 115/116 replayed counter updates with
a candidate. This is **not** precision, recall or F1: the counter is
unreadable for 2,782 seconds, can update late, and does not identify
the delivered stone. One remaining update has outgoing-stone travel
but no matching delivery-side broadcast shot. The independent
complete-recording gate is still open.

Four counter changes initially lacked delivery-view associations. All
four have same-colour travel motion in both proposal channels near the
counter update. Postreview source inspection showed that three already
had emitted visual candidates immediately before that motion, with
wrong visual colour. Linking those counters to the existing events
reduces the candidate ledger from 133 to 130 records: 129 origin-view
windows and one travel-only observation. Each of the 116 replayed
counter updates attaches to one candidate; 14 visual candidates have
no counter link. Twelve observed counter-state discontinuities and
nine colour conflicts are preserved. This is an ordered evidence
ledger, not reconstructed settled boards, exact release timing or
simulation-ready stone trajectories.

## Frozen second full-match transfer

The [Slovakia–USA full-match transfer](slovakia-full-transfer/RESULTS.md)
applied the same rules and a Slovakia-excluding origin model to a
different 7,616-second recording. Its reproducible runner completed
all 19 stages and found 495 broadcast shots. The counter was readable
for 4,517 seconds and gave 98 stable updates. Cap-only motion associated
88 updates; selected learned motion raised this to 89; the frozen
following-shot and existing-visual routes raised it to 94. The ledger
has 119 candidates, including 25 without a counter link. Four counter
updates remain unlinked, and 18 counter-state discontinuities remain.
These are transfer coverage diagnostics, **not** event precision,
recall or F1. They expose the next bottleneck: resolving competing
shot identities and throws seen only in travel/house views without
promoting false visual candidates.
Three source-selected windows yielded 13 agent-reviewed clear deliveries.
All 13 overlap a ledger candidate and one additional candidate is unmatched,
for a temporal development F1 of 0.963. Two matched colours conflict with
source review and two are unknown; colour-aware F1 is 0.667. The review
is small, agent-authored and uses coarse windows, so it does not qualify
as independent full-video F1.

## Third full-match development transfer

The [Sweden–Switzerland 2022 full-match transfer](swiss-full-transfer/RESULTS.md)
ran the same 19-stage pipeline with a Swiss-excluding origin model on
7,734 seconds. Its ledger has 121 provisional candidates, 99 counter-
backed and 22 visual-only, with four counter updates still unlinked.
Three source-hash-selected 300-second windows contained 15 clear
agent-reviewed deliveries; all 15 had one-to-one temporal overlap and
no extra candidates inside the evaluable spans. One matched colour was
unknown, giving colour-aware development F1 0.933. An experimental
earliest-following-motion hypothesis fills that one colour, but 11 other
colour changes occur outside those windows. These are narrow,
agent-authored diagnostics, not a full-match independent F1 result.
