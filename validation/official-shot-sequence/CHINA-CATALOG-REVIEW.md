# Systematic China candidate-object catalog

The [catalog runner](../../prototype/scripts/catalog_2024_event_patches.py)
replays **all 131** frozen provisional China 2024 events on the separate
360p video variant and saves three source-linked crops from each tracked
object. The [manifest](china-event-catalog-v1/manifest.json) records the
video/timeline/code/crop hashes and [seven contact pages](china-event-catalog-v1/Y_U6gzqORUs-contact-01.jpg).
It is a catalog of positive predictions, not an exhaustive throw reference.

Matching uses colour, crossing time within 0.15 s and image location. This
matters at R01-S157: two red raw tracks occur within 0.032 s, but one is at
x≈47 and the saved event is at x≈191. The spatial rule selects the latter,
whose [three crops](china-event-catalog-v1/crops/R01-S157-2.jpg) show a red
stone. Time/colour alone would have left the identity ambiguous. All 131
events replayed with no unmatched candidate under this rule.

The [development review record](china-event-catalog-review.json) identifies
four **non-stone tracks**: the previously reviewed broom R01-S173 and player
mark R01-S200, plus R01-S177 (wheelchair/equipment) and R01-S217 (person).
R01-S211 is a person-to-stone **identity merge**. The last three inspected
cases have full-frame
source strips at [S177](china-S177-full-frames.jpg),
[S211](china-S211-full-frames.jpg) and [S217](china-S217-full-frames.jpg).
The four non-stone tracks are likely false throw events from the short source
clips. R01-S211 is different: the track begins on a person or wheelchair,
then switches onto a red stone travelling up the left view. The
[crossing sequence](china-S211-crossing-sequence.jpg) and tracked observations
at 6876.3–6877.1 s support a real red delivery near its 6876.522 s crossing.
Its early three-patch catalog row shows only the person, illustrating why
whole-track appearance sampling mislabels a real event.

This distinction changes the detector design. A non-stone track can invalidate
*that track segment's* physical identity while leaving the throw hypothesis
alive. A future reconciler must detect identity switches and search for the
visible stone or other delivery evidence before suppressing an event. The official eight-end count discrepancy
does not identify which candidates are extras. No frozen timeline, event
decision, or full-video F1 estimate was changed by this source inspection.
