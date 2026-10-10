# Full China 2022 shot-evidence scale test

This is a **development** run on the already exposed Canada–China 2022
Paralympics source (`qn9tHfcimlQ`, 0–8356 s). It is not the reserved
independent recording and has no exhaustive throw-event labels.

The 5 Hz hard-cut scan found 630 broadcast shots across the full match.
The cuts inside 300–600 s exactly match the earlier fixed-interval scan.
The frozen China-excluding shot-origin model proposed 129 delivery-looking
shots. The original broadcast counter audit has 119 decrements and was
unreadable for 2,782 of 8,356 sampled seconds. A preserved postscore
counter-state replay removes three duplicate graphic-blink updates,
leaving 116 decrement observations for the later comparisons. Neither
counter version is a complete event reference.

The first full-source visual pass detects coloured-cap motion **within**
each camera shot, then checks for the same colour in the immediately
following shot. This avoids treating a coordinate match across a camera
cut as stone identity. Cap motion alone associated 92 of the replayed
116 counter changes with a shot. The selected learned-box audit scanned
164 shots (11,949 sampled frames) around unresolved counter windows,
weak origin scores and visual-only candidates, increasing association
to 100/116.

A later [2022 camera-family cap-continuation audit](../../official-shot-sequence/CHINA-2022-CAP-CONTINUATION-SCALE-TRANSFER.md) probes every one of the 160 frozen shot-scoped cap tracks for one additional in-shot half-second frame. It finds that simply scaling the Czech 2024 cap-size threshold by image resolution rejects many visible 2022 caps; a post-inspection previous-cap-size gate has better candidate-step coverage but is not independently validated. The existing shot-cut boundary remains essential.

A separate, postscore route for strong delivery views that cut away
**before** a sustained track forms in the current shot, with both
channels seeing the counter colour immediately in the next shot,
raised association to 112/116. It preserves four unassociated updates.
The resulting fusion contains 129 candidate shot windows; six have
counter/visual colour conflicts and retain unknown colour. A permissive
one-to-one temporal comparison can pair 115 of the 116 replayed counter
updates with a candidate within 45 seconds. The remaining yellow update
has travel-shot motion but no delivery-looking shot candidate of that
colour. Assigning the preceding red view to it would be misleading.
This is a concrete failure mode when the broadcast does not show the
throwing side of a delivery.

A first travel-view fallback recorded four provisional cases for the
four counter changes left unassociated with delivery-side shots. Source
review then showed that three already had an emitted delivery-looking
candidate immediately before the travel shot. Its visual colour was
wrong because another stone's motion dominated. A postreview link
attaches those three counter changes to the **existing** candidates
and leaves their colour conflicted, avoiding duplicate event records.
The fourth remains a travel-only candidate: both cap and learned
channels observe yellow motion, but no reliable yellow release view is
present. Its release window is broad. The four shorter reviewed intervals
with both channels gained no travel-only candidates. None of these
postscore rules is independently validated.

The [current candidate event ledger](candidate-throw-event-ledger-after-link.json)
orders 129 origin-view and one travel-only record. All 116 replayed
counter updates attach to one candidate; 14 additional visual
candidates have no counter link. Nine counter/visual colour conflicts
remain unknown. The ledger attaches observed remaining-stone counts
but flags 12 breaks in counter-state continuity instead of
interpolating a board state. It has no settled-stone positions or
validated physical trajectories. The earlier 133-record ledger is
preserved for comparison.

The full run also exposed a timing assumption in the earlier counter
probe: one plausible delivery shot ends about 28 seconds before a
one-second counter update window. The probe now uses its declared
45-second maximum lag without the redundant 25-second restriction.
All five earlier 300-second association counts remain unchanged after
that correction; the older outputs are preserved with `-v1` suffixes.

These counts cannot be converted to precision, recall or F1: a counter
can change late or be unreadable, and a candidate can be a player,
displaced stone or wrong physical identity. Exact release times and
throw-end boundaries remain unresolved.

The later [identity audit](identity-ambiguity-audit-v2.json) leaves this
ledger intact. It finds no visual-only colour-collision risk under its
narrow missing-same-shot-motion flag, but proposes six exploratory
alternative colours from earliest motion in the following shot.
Targeted source [checks near T123](hypothesis-followup-7550/sheet-01.jpg)
and [T130](hypothesis-followup-7930/sheet-01.jpg) show yellow deliveries
where the ledger says red. These are model-selected retrospective checks,
not an independent colour-accuracy estimate.
