# Full-recording right-view transfer: Canada–Scotland 2024

The unchanged 1 Hz right-colour proposal and entry tier ran over **0–7346 s** of the full 640×360 Scotland source. The [raw scan](right-entry-transfer/scotland-full-0-7346-raw.json) contains **228** colour tracks and **35** frozen-rule prefixes. The separately retained [postreview y=235/y≤225 variant](right-entry-transfer/scotland-full-0-7346-variant-235-225.json) preserves all 35 and adds nine, for **44 right-entry review prefixes**. The 11 variant prefixes within the previously tested 1650–2760 s interval exactly match the earlier transfer by colour and crossing time, despite track IDs changing in the full run. That is an internal reproduction check, not accuracy validation.

The [camera-aware fusion replay](right-entry-transfer/scotland-full-0-7346-camera-aware-fusion-v2.json) gives **33 conditional same-colour, left-before-right links**. It leaves 11 prefixes without such a link:

| Fusion status | Prefixes | Development source review |
| --- | ---: | --- |
| Right entry in routed left-layout gap | 8 | Seven short moving-stone paths (R067, R069, R073, R075, R127, R128, R214); one player/wheelchair path (R215). |
| Unmatched with the whole 20-second left lookback supported | 2 | R091 and R149 follow people or wheelchairs. |
| Right entry supported, prior left lookback crosses a coverage gap | 1 | R181 follows a moving yellow stone. |

The [44-prefix source-strip manifest](right-entry-transfer/scotland-full-0-7346-source-review/manifest.json) hashes first, line and confirmation frames for every right proposal. The [11-row development review](right-entry-transfer/scotland-full-0-7346-noncorroborated-source-review.json) classifies only the noncorroborated short prefixes; the 33 linked paths were **not** exhaustively source-classified by this review. These agent observations are not independent physical throw labels, and three frames per path cannot prove a complete delivery.

R181 exposes a camera-coverage boundary failure in the earlier fusion wording. Its right entry is at **6216.83 s** inside a supported run beginning at **6210 s**. The [two-panel lookback sheet](right-entry-transfer/scotland-full-0-7346-lookback-gap-review/r181-lookback-gap.jpg) shows a yellow stone moving through the left panel at about 6206–6210 s, then through the right panel after 6212 s. The first part falls inside the timeline's **6120–6210 s layout gap**, so absence of a left candidate cannot be treated as evidence against the right entry. The revised [fusion code](../../../../prototype/camera_aware_right_fusion.py) checks source support across the entire possible 20-second left-before-right interval when no left match is found. It records R181 as `right_only_prior_left_coverage_gap_review`, preserving uncertain cross-view identity and leaving it unaccepted. R091 and R149 remain unmatched under fully supported lookbacks. A regression test covers the boundary and the fully supported case.

This transfer broadens full-match evidence beyond Czechia and Latvia and identifies a concrete route-boundary recall opportunity. It does **not** establish full-match throw precision, recall or F1: the right rule was developed on exposed 2024 recordings, the left timeline has routed gaps, only 11 noncorroborated prefixes received targeted source review, and there are no exhaustive independent throw labels. The resulting paths are review evidence, not exact release/settle times or simulation-ready game states.

## Conditional replay with the existing bridged left timeline

The already saved [Scotland gap-bridge development timeline](scotland24-bridged-development/timeline.json) includes the six interior 90-second chunks omitted by the original route. Re-running the same camera-aware fusion on that timeline produces [41 conditional links and three unmatched reviews](right-entry-transfer/scotland-full-0-7346-bridged-camera-aware-fusion.json). **All eight** previously right-only source-reviewed moving-stone prefixes gain one earlier same-colour left candidate; the three reviewed player/wheelchair prefixes R091, R149 and R215 remain unmatched.

| Right stone prefix | Conditional earlier left ID | Lag | Left ID in original timeline? |
| --- | --- | ---: | --- |
| R067 | R01-S56 | 7.708 s | No |
| R069 | R01-S59 | 9.871 s | No |
| R073 | R01-S61 | 9.708 s | Yes |
| R075 | R01-S63 | 9.237 s | No |
| R127 | R01-S116 | 11.352 s | Yes |
| R128 | R01-S117 | 9.835 s | No |
| R181 | R01-S160 | 12.373 s | No |
| R214 | R01-S181 | 10.291 s | No |

The two original left candidates were visible before a routed gap while their right entries fell inside it. The other six are added bridge proposals and still need physical-stone verification. In particular, the saved Scotland bridge also contains source-reviewed clothing and changeover false paths; **41 conditional links do not validate all 122 bridged left candidates**. Time/colour agreement and selected source strips support a recall-oriented review tier, not a measured event detector or a verified physical cross-camera stone identity.

## Development check of a possible cross-view filter

The [source crossing review](scotland24-bridged-development/bridge-crossing-source-classes-development.json) classifies the **ten new** bridged left candidates at their tracked crossing point. The [reproducible audit](scotland24-bridged-development/bridge-cross-view-source-audit.json) joins those IDs to the frozen full-recording right-view links, checks source and artifact hashes, and gives this diagnostic:

| Source object at tracked crossing | Later conditional right-view link | No link |
| --- | ---: | ---: |
| Clear stone | 5 | 0 |
| Clear non-stone (jersey, players, wheelchair hardware) | 0 | 4 |
| Occluded / identity uncertain | 1 | 0 |

This supports using a later same-colour right-view prefix as **additional evidence for review**, especially for recovered left-layout gaps. It does not justify requiring a right link to accept every throw: the source review covered only selected detector proposals, the left crossing and right prefix are not proven to be the same physical stone, and an occluded case remains unresolved. The ten cases were exposed during development and labeled by the development agent. The table is **not a precision, recall, F1, or independent filter validation result**. A filter operating point needs exhaustive independent event labels from held-out recordings, including true throws that neither camera proposal finds.

A separate [negative-control replay](scotland24-bridged-development/cross-view-negative-controls.json) checks whether 41 links merely follow from dense left candidates. It circularly shifts the 44 right-entry timestamps together in 30-second increments: the **244** shifted replays yield **0–13** links (median **7**), and none reaches the observed **41**. Swapping red and yellow claims at the original timestamps yields **one** link. The [runner](../../../../prototype/scripts/audit_scotland_cross_view_nulls.py) verifies hashes against the saved right proposals, bridged timeline, fusion output and code before replaying the controls. This shows the *conditional matching signal* depends strongly on actual timing and colour in this exposed recording. Shifted entries are synthetic and dependent; the comparison is neither a calibrated significance test nor proof that any link joins the same physical stone. It does not measure throw precision or recall.

## Ordered evidence for game-state reconstruction

The [camera-observation-window export](scotland24-bridged-development/candidate-multiview-observation-windows-v2.json)
now joins the ordered candidate sequence to the saved left raw track points
and right entry prefixes, with matching source hashes, colours and crossing
times required. It retains **125** review rows: **41** conditional two-view
pairs, **81** left-only observations and **three** right-only observations.
For the 41 pairs, the median observed left and right spans are **4.7 s** and
**5.0 s**; the median gap with no tracked camera observation is **3.0 s**
(range **1.1–7.0 s**). The median first-left-to-last-right envelope is
**11.7 s**. This is a concrete candidate-level segmentation handoff for
analysis, with the unobserved seam explicit. It does **not** establish release,
settle, persistent cross-camera identity, physical throw boundaries, or a
continuous trajectory. The three right-only rows were previously
source-reviewed as people or wheelchairs and remain review evidence, not
events. Reproduce with
`prototype/scripts/export_candidate_multiview_observation.py`; its artifact
pins the three inputs and exporter code by SHA-256.

### Source pixels inside the apparent camera gap

The largest exported seam, R01-S160, is **6206–6213 s** by the existing
trackers. Source frames show its yellow stone continuing in the left overhead
view beyond the saved left-track endpoint and appearing at the bottom of the
right panel before the saved right-prefix start. A second exposed seam,
R01-S01, shows the right-panel stone at **129–131 s** although the saved right
prefix starts at **132 s**. At 129–131 s its yellow contour is larger than the
original right probe's 120-pixel area ceiling; the first frame is also below
its y=325 image cutoff. These are *detector observation gaps*, not proof that
the stone is invisible between views.

The [right-backward source-pixel diagnostic](scotland24-bridged-development/right-backward-seam-diagnostic-v2.json)
revisits **all 41** conditionally linked pairs with a bounded right ROI ending
at image y=360 and a 220-pixel colour-contour area ceiling. Starting from each
saved right prefix, it follows only a unique same-colour blob in consecutive
one-second source frames, requiring forward upward motion and a bounded
position and area change. It finds earlier right pixels for **39/41** pairs;
the median *conditional* camera gap falls from **3.0 to 0.9 s** (median
reduction **2.0 s**). R01-S01 gains the 129–131 s pixels and falls from a
3.5 s to a 0.5 s seam. R01-S160 gains 6211–6212 s pixels and falls from a
7.0 s to a 5.0 s seam; its still-visible left pixels have not been tracked
beyond 6206 s by this right-only diagnostic.

This is a development probe fitted after inspecting Scotland, and the 41
pairs were already selected by the old detector. The backward associations
can switch to another yellow or red object, so none is promoted to a verified
cross-camera stone path or physical throw boundary. The result identifies a
specific missed-observation mechanism and a concrete next detector test:
apply the wider right extraction on entire held-out recordings and score
source-first throw recall and false positives, including stone return motion.
The [fixed Czechia transfer](RIGHT-ENTRY-CZECH-FULL-RESULTS.md#fixed-expanded-roi-backtracking-transfer)
finds earlier pixels for 38/40 source-reviewed stone prefixes **and** 3/5
reviewed person or wheelchair prefixes; backward continuity is therefore an
observation aid, not a throw filter.
The [candidate transfer summary](EXPANDED-RIGHT-ENTRY-TRANSFER-RESULTS.md)
also records proposal counts and selected false paths in Czechia, Italy and
Estonia with the expanded extractor fixed.

The [full-match candidate sequence](scotland24-bridged-development/candidate-game-state-sequence.json) now retains **all 122** bridged left proposals and **three** unlinked right prefixes in time order. Each row carries its proposal origin, source crossing review where available, conditional right link, and explicit unknown release, settle, end, board, persistent stone ID, metric path and spin fields. It is an evidence handoff, not 125 verified throws or a game-state trajectory. Seven rows are source-reviewed non-stones (four left crossings, three right-only people/wheelchairs); five newly bridged rows are source-reviewed stones with conditional right links; one new crossing remains occluded. The remaining 112 left proposals have no crossing-level source classification in this audit.

The [exporter](../../../../prototype/scripts/export_scotland_candidate_sequence.py) checks artifact hashes and the bridge's explicit old-to-new ID map. This matters because merging the formerly separate supported runs renamed **74** baseline candidate IDs; comparing IDs alone would falsely treat them as new throws. The sequence keeps original IDs beside renamed IDs while preserving crossing time and colour. No row is marked simulation-ready. Physical shot identity, complete post-throw boards and calibrated trajectories still need source-backed validation before this sequence can drive coaching simulation.

### Post-entry partial image boards

An unchanged **Latvia-developed** right-camera cap rule was replayed over all 44 Scotland right prefixes. The [source-video scan](scotland24-bridged-development/right-entry-partial-cap-scan.json) finds three-frame stable colour-cap *proposals* after **37** entries (**68** local cap blobs). It abstains for scene/player motion after five, sees no stable cap after one, and abstains for one because the next right entry falls too close to the +25 s sample. All three source-reviewed person/wheelchair prefixes fall in the motion-abstention group. This is a transfer result at fixed thresholds, not a labelled stone-board accuracy result.

The [painted-house alignment audit](scotland24-bridged-development/right-entry-house-alignment.json) can probe 33 adjacent right-entry pairs. Of those, **17** pass the existing zero-translation and ≥0.7 blue-mask overlap gate; 16 abstain on alignment and ten more pairs lack a usable cap set. The [partial-state handoff](scotland24-bridged-development/candidate-partial-state-handoff.json) attaches these observations to the 125-row evidence sequence and records **21** conditional camera-local cap matches across the 17 passing pairs. It does **not** infer stone additions, removals, scoring, end continuity, physical settle time, or a complete board. A stable-looking coloured blob may still be a nonstone, and one sampled frame per event cannot prove camera pose throughout the interval. All 125 rows remain below simulation readiness.
