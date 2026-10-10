# Right-view entry tier over the full Canada–Czechia 2024 recording

The fixed 1 Hz right-colour proposal and tracker ran over **0–6683 s** of the full 640×360 source. It produced **276 raw tracks** and **38** prefixes under the original y=250/y<=220 entry tier. The separately retained postreview y=235/y<=225 variant preserves all 38 and adds seven, for **45 review prefixes**. This is a development pass on an exposed recording, not an accepted throw timeline or event F1 evaluation.

The [raw full scan](right-entry-transfer/czech-full-0-6683-raw.json) and [variant](right-entry-transfer/czech-full-0-6683-variant-235-225.json) retain source and code hashes, all raw tracks, and the exact observed prefix points. The [source-strip manifest](right-entry-transfer/czech-full-0-6683-variant-source-review/manifest.json) hashes first/line/confirmation frames for all 45 prefixes. In a same-agent [source review](right-entry-transfer/czech-full-0-6683-source-review.json), **40** short prefixes visibly follow moving stones and **five** follow people or wheelchairs: R028, R136, R140, R174, and R265. The variant adds six stone paths **and R140, a person path**. Three sampled frames do not prove complete physical throws or identify a stone across cameras; these are exposed development judgments, not independent precision labels.

The [conditional cross-view join](right-entry-transfer/czech-full-0-6683-left-state-links.json) uses same colour and a preceding accepted left event within 20 seconds. All 40 source-reviewed stone prefixes pair with **distinct** earlier left candidate IDs; all five person prefixes have no such match. Of the 40 paired left events, **35** have an existing partial stable camera-local post-event board, three have no stable stones in their registered tails, and two have no quiet tail. None is a complete physical game state or simulation-ready. The join is useful corroboration where the left view is active, but making it a universal hard filter would discard the right-only review proposals in recordings whose left view freezes.

The [layout audit](right-entry-transfer/czech-full-0-6683-layout-audit.json) routes 90–6570 s as supported split-screen, with 0–90 and 6570–6683 s unknown. All 45 entry frames have the split-screen signature and lie in supported runs. The five person paths survive this layout check, showing that camera routing and object identity are separate problems. The [unmatched-prefix source strips](right-entry-transfer/czech-full-0-6683-unmatched-right-review/manifest.json) show the five player/wheelchair paths explicitly.

The same fixed [five-second panel-motion audit](right-entry-transfer/czech-full-left-freeze-audit.json) reports no **60-second-or-longer** static-left run entirely within the 90–6570 s supported segment. It finds 0–70 s and 6525–6610 s runs at the recording edges; the latter overlaps the final supported block and needs play-phase review. This sparse audit cannot rule out shorter frozen-left intervals or occluded deliveries.

The full-match result therefore supports a **camera-aware corroboration tier**: time/colour links can prioritize right entries when left evidence is available, while entries during documented left-camera blindness remain review candidates. It does not establish right-only full-match recall, physical stone identity, release/settle timing, complete boards, or reliable simulation parameters. Independent exhaustive throw labels and source review of unpaired intervals remain necessary before any high-F1 claim.

## Fixed expanded-ROI backtracking transfer

The [source-hashed transfer audit](right-entry-transfer/czech-full-right-backward-transfer.json)
applies the Scotland-developed expanded right-camera contour extraction and
unique backward colour association to **all 45** Czechia right-entry prefixes,
without changing its thresholds. It finds earlier right-camera pixels for
**41/45** prefixes. Against the *existing same-agent three-frame source
review*, that is **38/40** moving-stone prefixes and **3/5** people or
wheelchair prefixes. Median added duration among the extended stone paths is
**1.5 s**, versus **2.0 s** among the three extended nonstone paths.

This transfer shows that the original near-camera ROI and contour ceiling
omit useful pre-entry observations on another recording. It also shows that
backtracking **cannot be used as a throw-versus-person filter**: it follows
several reviewed nonstone paths. The associations remain conditional image
motion, and the selected-prefix sample gives no full-match recall or F1.

The separate [complete-source expanded extraction](right-entry-transfer/czech-full-expanded-right-first.json)
tests the actual proposal cost instead of only backtracking selected old
prefixes. On the same 0–6683 s source, the wider ROI/220-pixel area ceiling
produces **291 raw tracks** and **40 original-tier entry reviews**, compared
with **276 raw tracks** and **38 original-tier entries** from the frozen scan.
All 38 original entries have a same-colour expanded entry within three
seconds; there are **two additional expanded entries**. These are proposal
matches, not verified physical identities. This comparison uses the original
y=250/y≤220 entry tier on both sides; the separately saved 45-entry
y=235/y≤225 variant is not replaced by the 40-entry diagnostic.

The [two additional source strips](right-entry-transfer/czech-full-expanded-novel-source-review/manifest.json)
show why a recall-only change needs a filter. **E120** at 2620.091 s follows
a moving red stone in the right view and has a conditional same-colour left
candidate **S63** at 2609.269 s (10.822 s earlier). S63 was already retained
by the left motion/patch screen and has separate provisional receiving-view
motion, so E120 adds right-entry corroboration rather than a newly counted
physical throw. **E279** at 6268.429 s follows a red-clad player/wheelchair;
another expanded track near it matches the existing reviewed person prefix
R265. E279 is a new false review trigger. These are source-frame development
judgments, not independent validation. The proposed widened detector must
keep an explicit person/scene filter and be scored on independent exhaustive
throw labels before replacing the frozen rule.

The existing **underpoint** cue was then applied *unchanged* to the widened
prefixes. A [source-hashed class handoff](right-entry-transfer/czech-full-expanded-source-class-transfer-v2.json)
maps the 38 time/colour-paired prefixes to their prior same-agent source
reviews and keeps the two new source-strip reviews explicit. The
[40-prefix feature replay](right-entry-transfer/czech-full-expanded-underpoint-transfer-v2.json)
sends all **35** reviewed moving-stone paths to clear-context review and all
**five** reviewed person/wheelchair paths to cluttered review at the existing
0.25 median non-ice cutoff. The class transfer's maximum crossing-time
difference is 0.012 s. Nine prefixes have only two available underpoint
samples; E120's near-camera first frame is one of them. E120's available
median is **0.0109**, while E279's is **0.8493**. This is encouraging on the
exposed Czech source, but classes are inherited through candidate matching
or supplied by the detector developer, and the cue was itself developed on
other exposed recordings. It is a review-tier diagnostic, not independent
throw precision or a safe automatic event acceptance rule.
The fixed wider extraction also has a [cross-recording transfer summary](EXPANDED-RIGHT-ENTRY-TRANSFER-RESULTS.md)
for Italy and Estonia intervals.

## Fixed right-view board-sampler transfer

The previously used right-camera cap sampler was replayed, **without Czechia-specific threshold tuning**, after all 45 full-recording right prefixes. The [source-video scan](right-entry-transfer/czech-full-right-entry-partial-cap-scan.json) finds three-frame stable colour-cap proposals after **32** entries (88 local blobs). Seven entries have no stable proposal, four abstain for scene/player motion, and two abstain because the next entry is too close to the +25 s sample. Among the 40 prefixes source-reviewed as moving stones, 30 have a stable cap set; among the five reviewed as people/wheelchairs, **two also have stable cap sets** (R174 and R265). This is direct evidence that a later visible board cannot validate the triggering event. Those two rows remain source-reviewed nonstone prefixes.

The [painted-house alignment probe](right-entry-transfer/czech-full-right-entry-house-alignment.json) can compare 25 adjacent entry pairs. The [camera-local cap sequence](right-entry-transfer/czech-full-right-entry-cap-sequence.json) lets **24** pairs through the existing zero-translation and ≥0.7 painted-ring overlap gate and records **60** conditional local cap matches; 19 pairs lack usable cap sets and one fails image alignment. These matches are pixel associations between incomplete views. They do not establish persistent stone identity, a physical board transition, an end boundary, or simulation-ready state. Compared with [Scotland's fixed-rule replay](RIGHT-ENTRY-SCOTLAND-FULL-RESULTS.md#post-entry-partial-image-boards), this transfer shows the sampler can return partial image evidence in another match, while its false-event counterexamples prevent using board presence as a throw filter.
