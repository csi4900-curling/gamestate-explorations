# Korea–China 2022: frozen first full-match transfer

The [selection and model hashes](SELECTION.md) were recorded before any local
video frames or detector predictions were inspected. The source is the
[Paralympic Games full replay](https://www.youtube.com/watch?v=ia3HIF_4Bdo),
measured at 6,829.667 s; the unchanged pipeline ran on 0–6,829 s, leaving a
declared 0.667 s tail. The independent [official results book](https://curlit.com/PDF/PWG2022_ResultsBook.pdf)
lists six ends of 16 numbered shots, **96 deliveries**, with 48 red and 48
yellow handles. The extracted [shot ledger](../../official-shot-sequence/pwg2022-korea-china-official-ledger.json)
and [diagram ledger](../../official-shot-sequence/pwg2022-korea-china-official-boards.json)
contain 96 post-shot boards and 316 parsed symbols; 19 diagrams have parser
review flags. None supplies video delivery times.

| Frozen first-pass output | Count |
| --- | ---: |
| Provisional event candidates | 103 |
| Official numbered shots | 96 |
| Candidate count minus official count | +7 |
| Readable broadcast-counter decrements | 81 |
| Counter-linked candidates | 81 |
| Visual-only candidates | 22 |
| Counter-backed colour conflicts | 9 |
| Unresolved broadcast-counter changes | 23 |

The 103 candidates comprise 102 origin-view candidates and one travel-only
counter candidate. Their stated colours are 57 red, 31 yellow and 15 unknown.
Among counter-linked candidates, 71 have a resolved colour, nine carry a
visual/counter colour conflict, and one uses only the counter colour. Of the
22 visual-only candidates, 15 are red, one yellow and six unknown.

The colour totals expose a failure even without timestamps: **57 known-red
candidate claims exceed the 48 official red deliveries by at least nine**,
so all those claims cannot be distinct correctly coloured match throws.
Conversely, even assigning all 15 unknown candidates yellow yields at most
46 yellow-labelled candidates for 48 official yellow deliveries. At least
two official yellow shots therefore lack a yellow-or-unknown candidate under
that one-to-one interpretation. A wrong colour, duplicate proposal,
non-stone motion, out-of-match proposal or missed physical throw could explain
individual discrepancies; the count bounds do not classify specific events.

The source-only [first-transfer artifact](FIRST-TRANSFER.json) records hashes
for every pipeline stage. This is another match in the **same Beijing 2022
broadcast family**, not proof of transfer to a new camera production. A
delayed counter decrement is an event proxy, and the official book has no
video timestamps. The 81 counter associations and 103-versus-96 comparison
are therefore **not precision, recall, F1, verified physical throw identities,
or release-time accuracy**. The result stays frozen; any investigation or
rule change on this match is subsequent development and needs another
untouched recording for validation.

To replay the exact source-only pass, run
`feasibility/scripts/python.sh prototype/scripts/run_full_shot_evidence.py --video validation/throw-event-benchmark/paralympics-2022-korea-china/source.mp4 --source-id ia3HIF_4Bdo --start 0 --end 6829 --origin-model validation/curlobserver-learned-probe/shot-origin-pair-v1/model-excluding-swiss-dev.npz --learned-model validation/curlobserver-learned-probe/model-v1/model.npz --output validation/curlobserver-learned-probe/korea-china-full-first-transfer`.
The runner checks hashes of existing stages and resumes only missing stages.

## Postscore source-only colour diagnosis

After freezing the result above, the unchanged post-cut colour rule from
earlier Beijing recordings was applied to the 22 visual-only candidates.
Its [sidecar](VISUAL-ONLY-POSTCUT.json) proposes a unique receiving-view
colour for 13, abstains on nine, changes four original **red** proposals to
**yellow**, and newly proposes colour for five originally unknown candidates.
The original 103-candidate ledger has not been edited. The
[source-frame sheet](red-yellow-postcut-conflict-frames.png) shows yellow
stones in the origin and receiving views around the four conflicts. It does
not independently establish that the same physical stone crosses the cut.

The older held-cap release cue fires with yellow and passes its below-ice
check for one conflict, T099; it abstains on the other three. Thus a generic
held-cap cue cannot simply replace the red motion rule. The red tracks in
those origin views include players' red gloves and equipment near the stone,
and T001's original cap-motion record contains four red same-shot tracks
plus a yellow following-shot track. The current two-shot confirmation can
choose red when an unrelated red track occurs on both sides of the cut.
This is a concrete identity-filter failure mechanism, **not** a measured
false-positive count. Any new filter based on these frames must be frozen
and tested on a different untouched recording.

A reproducible [origin-ice countercheck](ORIGIN-ICE-CONFLICT-PROBE.json)
rescans the four conflict windows with the existing cap tracker and broad
white-ice-below feature. **All four** still contain at least one red motion
track whose median below-patch ice fraction is at least 0.6. That feature
alone cannot remove the contradictory red evidence. This is a selected
postscore failure case, not a general estimate of an ice filter's accuracy.

The existing cross-match cap-context classifier was also run, unchanged, on
every point of those four conflict windows. The reproducible
[patch-identity audit](ORIGIN-CAP-PATCH-CONFLICT-PROBE.json) finds 23 red motion
tracks in total; at least one red track has an accepted median patch score in
**three of the four** windows. Most red tracks are rejected, but the classifier
does not eliminate the contradictory red evidence consistently. These are
postscore selected cases, and a stone-like patch score is not a physical
throw identity. Neither this score nor the broad ice cue is justified as a
hard event veto from these data.

An [image-space track-geometry pilot](ORIGIN-TRACK-GEOMETRY-PILOT.json)
compares the same four conflict windows with five counter-backed red candidate
windows. The red tracks overlap in path straightness and vertical direction:
for example, conflict T101 has red tracks with net-to-path ratios 0.917 and
0.974, while red tracks in counter-backed T006 and T008 score 0.786 and 0.809.
The tracker can associate clothing or switch objects, and counter support does
not label an individual red track. A single straightness or monotonicity
threshold therefore is not justified as a stone-identity filter.

The [stone-box model swap pilot](STONE-BOX-MODEL-SWAP-PILOT.json) reruns the
frozen v1 detector and the previously trained public-tracking v2 detector at
2 Hz in those same nine selected windows. The newer model reduces red boxes
and tracks in T001 (103 to 36 red boxes; five to one supported red tracks),
but does not eliminate its contradictory red track. In counter-backed T006,
it reduces 154 red boxes to 11 and six supported red tracks to zero. Neither
model produces a supported yellow track in any of the four selected conflict
windows. The public tracking set's box-level gain therefore does not justify
replacing the full-match detector on this broadcast. The selected windows and
counter controls are diagnostic, not independent event labels.

For downstream state work, the derived
[visual-only colour handoff](VISUAL-ONLY-COLOUR-HANDOFF.json) preserves both
view observations without editing the frozen event ledger. Among the 22
visual-only candidates, four have agreeing view colours, four conflict, eight
have only an origin-view colour, five only a receiving-view colour, and one
has neither. Even the four agreements remain identity-unverified and are
explicitly marked not game-state-ready. This prevents a contradictory visual
colour from silently becoming a settled stone state.

## Shot-order and state handoff

The unchanged official/counter slot aligner maps all 81 readable decrements
to unique, colour-consistent positions in the 96-shot published order. The
[96-slot handoff](../../official-shot-sequence/korea-china-official-counter-slot-handoff-first.json)
retains 80 origin-view candidate links, one travel-only counter candidate,
and **15 explicitly unassigned counter slots**. It attaches each official
post-shot schematic diagram and turn direction as reference data. The
15 missing counter slots remain unassigned even though 22 visual-only
candidates exist, because proximity alone cannot establish their physical
shot identities. Video post-shot boards and physical simulation readiness
remain unknown for every slot. This handoff is a reproducible game-state
reference and evidence scaffold, not a reconstructed video game state.

The [counter-gap candidate audit](COUNTER-GAP-VISUAL-CANDIDATES.json) places
all 22 visual-only proposals between adjacent counter-linked official slots,
using only their time order. Six gaps have exactly one missing official slot
and one visual proposal, so they are useful **review targets**, but neither
the candidate's physical throw identity nor its official-slot association is
verified. Five other visual proposals occur where the anchored official order
has no missing slot. Two gaps have more visual proposals than missing slots;
one gap has fewer, and one has two of each with ambiguous identity. This
accounts for all 15 missing slots and all 22 visual-only proposals without
silently assigning extras to game states or claiming event precision/recall.

### Internal-edit recall diagnosis at the end-five boundary

The gap between counter anchors B71 and B72 contains two unanchored official
red shots but only one visual-only candidate. Source frames around 5170–5229 s
show yellow-stone travel, a house view, then a new red delivery view and red
travel; the [source-frame strip](S372-transition-frames.png) shows selected
moments. The frozen camera-shot manifest groups the first three phases into
S372 (5170.8–5206.2 s), for which the event ledger emits only the
counter-linked yellow T085. The later red origin has no separate camera-shot
entry.

The [bounded S372 probe](S372-UNDERSEGMENTATION-PROBE.json) measures source
frame changes at 5180.6 s (gray change 53.411, histogram distance 0.3429)
and 5195.6 s (68.783, 0.3157). Both miss the frozen 0.35 histogram hard-cut
threshold. A postscore 0.30 threshold
[full-source scan](../../curlobserver-learned-probe/korea-china-full-first-transfer/possible-edits-0_30.json)
finds 48 additional possible edits across 44 existing camera shots; the
[temporal audit](../../curlobserver-learned-probe/korea-china-full-first-transfer/possible-edits-0_30-temporal.json)
calls 42 of these isolated spikes. At 5195.6 s, gray and histogram changes
are respectively 20.52 and 6.239 times the larger adjacent flank, satisfying
the previously used 2× isolation rule. The 5180.6 s change does not pass that
rule.

Splitting S372 **only at the isolated 5195.6 s proposal** gives a late
5195.6–5206.2 s segment that the unchanged shot-origin model scores 0.958.
The existing cap-motion and adjacent-shot confirmation rules then emit a
[separate red corroborated candidate](S372-ISOLATED-CUT-RESCUE.json) with
red motion in that segment and in S373. The early segment scores 0.0086 as
an origin. This is a concrete route to recovering a candidate lost by
undersegmentation, but the clip and threshold are exposed development data.
The red cap tracks can include clothing or other stones, and neither a camera
edit nor same-colour motion verifies a physical delivery. The frozen 103-event
first pass and 96-slot state handoff remain unchanged; the edit rule needs a
separate transfer test before promotion.
