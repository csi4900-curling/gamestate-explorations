# Full-match candidate and partial-state evidence union

The [source-checked chronological handoff](full-match-evidence-union-development.json) combines the Czech full-match early-ROI scan, the 91-candidate left-bound development screen, the six distinct pre-split motion review proposals, their post-window boards, and the 45-entry right-view source review. It retains **all 147 raw left-trigger IDs** instead of silently turning every observed motion window into a throw.

| Evidence tier | Raw IDs | Meaning |
| --- | ---: | --- |
| Screen provisional | 91 | Passed the integrated motion and appearance screen; includes agent-reviewed false paths S96 and S143. |
| Pre-split review only | 6 | Visible incoming motion stops at the first ambiguous branch; no post-contact identity is selected. |
| Duplicate pre-split trigger | 1 | S132 repeats S131's shared prefix and is kept as a raw trigger, not a second event proposal. |
| Other unselected raw triggers | 49 | No event-state promotion in this union. |

Among the 97 screen-or-review windows, **84** have a partial stable post-window board (78 screen candidates, six pre-split windows). These are camera-local coloured-object observations, not complete settled physical boards; the S40 board is known to omit a visible yellow stone. The union attaches **40** source-reviewed moving-stone right prefixes as conditional same-colour, 0–20-second links to screen candidates. The other **five** right prefixes remain separate unmatched reviews; source strips show people or wheelchairs. The links do not prove one physical stone travelled between cameras.

Each raw row records its original passage time and colour claim, screen status, evidence tier, any partial board observations, any right-view link, and explicit unknown release, settle and spin fields on the promoted review rows. Every row has `physical_throw_verified: false` and `simulation_ready: false`. A row's absence from the 97-window group does not prove no throw happened; the raw trigger stage can miss deliveries entirely. The union is a practical review and state-handoff index, **not a full-match segmentation accuracy result**. Independent exhaustive throw labels are still required to calculate precision, recall and F1.

The [exporter](../../../prototype/scripts/export_full_match_evidence_union.py) checks source and lineage fingerprints and enforces exact accepted-ID agreement, one-to-one right links, prefix-board coverage, and duplicate-trigger accounting. Its input hashes are embedded in the JSON. It does not replace the frozen 79-candidate benchmark or the 91-candidate development screen; it joins their already exposed evidence without changing detector decisions.

## Longest candidate gaps

The [source-hashed gap packet](full-match-union-gap-review/manifest.json) samples the five longest gaps between adjacent screen-provisional or pre-split-review rows at 15-second intervals, retaining every intervening raw trigger ID. This is a **recall triage packet, not a negative throw label**: a stone can traverse the sampled view between stills.

| Candidate gap | Length | Intervening raw triggers | Sampled source context |
| --- | ---: | ---: | --- |
| [S96–S102](full-match-union-gap-review/gap-01-S96-S102.jpg) | 300 s | 5 | S96 is an agent-reviewed wheelchair false path. The sampled interval shows an empty rink, then ice preparation and players returning for the next end; S98–S100 coincide with that maintenance period. |
| [S139–S140](full-match-union-gap-review/gap-02-S139-S140.jpg) | 184 s | 0 | Players remain around a populated house during a long pause; the sampled frames do not show a clear new stone traverse before S140. |
| [S43–S44](full-match-union-gap-review/gap-03-S43-S44.jpg) | 120 s | 0 | Players discuss and position stones near the house; sampled frames do not establish an additional delivery. |
| [S120–S124](full-match-union-gap-review/gap-04-S120-S124.jpg) | 114 s | 3 | The sampled frames include stone clearing and an end reset around S121–S123. |
| [S69–S76](full-match-union-gap-review/gap-05-S69-S76.jpg) | 112 s | 6 | The sampled frames include stone clearing, an empty house, and restart preparation. |

This weakens the hypothesis that the largest chronological gaps are all missed deliveries, but it does not prove recall. The right next check is dense source review or independent throw labels in any remaining suspect interval, especially where a raw trigger has actual moving-stone evidence. None of these gap observations changes the detector or the 97-window evidence count.

## Displayed-end context

The [full 147-trigger marker alignment](full-match-display-context-development.json) reuses the existing 30-second, two-sided broadcast-marker bracket rule. The [joined handoff](full-match-evidence-union-with-display-development.json) attaches that exact context to each raw trigger after checking candidate IDs, times, source fingerprints and raw-ledger lineage. Among the **97** screen-or-review windows, **62** have a consistent displayed-end bracket, **33** have insufficient nearby marker evidence, and **two** (S51 and S76) are bracketed by a graphic change. The earlier S28 and S50 raw triggers also straddle a change but are not selected event windows.

The source graphic has six stable displayed-end runs, consistent with the official result book's six completed ends. That agreement does not timestamp physical end boundaries: the display can update late, and unknown intervals are left unknown. S51 and S76 are therefore explicit boundary review targets, not automatically assigned to the new or old end. Every joined row keeps `physical_end_identity: null` and `simulation_ready: false`. The [join code](../../../prototype/scripts/attach_full_match_display_context.py) records both input and code hashes.

The [source-hashed boundary sheets](full-match-display-boundary-review/manifest.json) sample both windows every two seconds. [S51](full-match-display-boundary-review/s51-display-change.jpg) shows a clear visible house before its red passage at 1968.083 s; the existing right-entry ledger conditionally links R094 at 1977.538 s, **9.455 s later**. [S76](full-match-display-boundary-review/s76-display-change.jpg) shows a yellow stone crossing the left view at 3114–3118 s after the visible house had been cleared. This is consistent with a first delivery after an end reset, but two-second stills cannot certify the whole sheet or physical end boundary.

S76 has **no right-entry link**. A yellow object moves down the right image at 3106–3110 s, before S76's left passage: the unchanged right-colour proposer places it at image y = 192, 223 and 276 px at 3106, 3108 and 3110 s. This earlier, opposite-direction motion cannot corroborate S76 under the left-before-right handoff rule. It is not evidence of a missed S76 right-camera receiving path. The [temporal-order regression](../../../prototype/tests/test_camera_aware_right_fusion.py) protects that rule; physical identity of the earlier right motion remains unknown.
