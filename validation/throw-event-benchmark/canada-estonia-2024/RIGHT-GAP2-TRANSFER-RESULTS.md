# Frozen gap-two right-view transfer on Canada–Estonia 2024

The [predeclared plan](RIGHT-GAP2-TRANSFER-PLAN.md) fixed the post-Italy two-second area-aware association, late seed, 1650–2760 s source interval and paired 0.25 context thresholds before this run. Estonia had prior right-view development work, so this is a same-production **development transfer**, not independent physical-delivery scoring.

The [fixed probe](right-area-aware-gap2-fixed-transfer.json) preserved 45 raw tracklets and emitted **17 review paths**. All 17 were shown in four [source strips](right-area-aware-gap2-source-review/manifest.json); [same-agent source-pixel classes](right-area-aware-gap2-source-review/source-prefix-classes.json) were saved before context scoring. Twelve short paths visibly follow moving stones, four contain stone pixels but have uncertain identity across a long track or crowded house, and A045 follows a wheelchair athlete.

| Source-visible proposed prefix | Clear context | Cluttered review |
| --- | ---: | ---: |
| Short moving-stone path | 12 | 0 |
| Stone pixels, identity uncertain | 2 | 2 |
| Person / wheelchair | 0 | 1 |

The [paired context result](right-area-aware-gap2-combined-context-transfer.json) flags the person and keeps all 12 short stone paths in clear review. The split among uncertain stone-pixel paths demonstrates that neither a clear nor cluttered context score establishes the physical stone's identity. A040 follows red pixels into a crowded house after the separate A041 red path; post-contact identity is unresolved.

The new paths overlap **15 of 17** earlier same-agent [coarse windows](blind-reference.json). E11 and E15 lack a new proposal. The *older* bidirectional tier overlapped only 11/17, but its [source-reviewed B018 path](../layout-router/full-2024-coverage/right-entry-transfer/bidirectional-fast-source-classes-development.json) covers E11 and visibly follows a moving stone. The set-union of the old reviewed E11 path and the new paths therefore has stone-pixel evidence in **16 of 17** windows, leaving E15. This is conditional proposal coverage, not throw recall: the two trackers can create duplicates, the coarse windows are same-agent still reviews, long-track identities remain uncertain, and no independent complete-end denominator exists.

This transfer contradicts a simple replacement of the old greedy association with the area-aware one: it gains several windows but loses a prior source-reviewed short stone path. A high-recall stage should preserve both proposal lanes, retain provenance, and deduplicate only after checking temporal, colour and object evidence. The next source audit should inspect E15 and the E11 association difference before changing the rules again. Cross-camera delivery links and settled boards remain unvalidated for game-state/simulation use.

The [lossless two-lane candidate union](right-proposal-lane-union.json) now retains all **29** proposals (12 older greedy plus 17 area-aware), with lane-qualified IDs and input fingerprints. It intentionally makes no event merge, acceptance or F1 claim; two proposals may refer to the same stone. Equivalent unions were saved for [Italy](../canada-italy/right-proposal-lane-union-postscore.json) and [USA](../canada-usa-2024/right-proposal-lane-union-postscore.json) as development artifacts.

## Subsequent global-assignment diagnostic and E15 limit

The [E11/E15 source sheet](right-e11-e15-postscore.jpg) shows both yellow stones in the right camera. In E11, the greedy area-aware linker lets an older track claim the y≈169 yellow observation at 2368 s, splitting the moving stone's sequence at y≈225, 205, 186. A global minimum-cost assignment gives that observation to the closer moving track and reproduces the older tier's 2365–2369 s stone path. This correction was devised **after** seeing the E11 miss.

The [full post-score global probe](right-global-area-postscore.json) emits 17 proposals. All were shown in four [source strips](right-global-area-source-review/manifest.json) and [source-classed](right-global-area-source-review/source-prefix-classes.json) before context scoring:

| Source-visible proposed prefix | Clear context | Cluttered review |
| --- | ---: | ---: |
| Short moving-stone path | 13 | 0 |
| Stone pixels, long-track identity uncertain | 2 | 1 |
| Person / wheelchair | 0 | 1 |

The [paired context result](right-global-area-combined-context-postscore.json) still distinguishes the one person path in this selected set. Global assignment puts reviewed stone pixels in **16 of 17** coarse windows, including E11; E15 remains missing. At 1 Hz in E15, the fixed colour proposal returns a yellow cap at 2610 s, then none at 2611–2612 s, then a cap at 2613 s. Their three-second gap exceeds the preserved two-second link limit. Even a 0.5-second diagnostic has discontinuous yellow detections. This is a colour-observation and short-track-continuity gap, not a camera absence and not something global matching alone can solve.

The global assignment is a post-score development change. Its unchanged Italy transfer is reported separately; neither the 16/17 overlap nor the context table measures physical-delivery recall or F1.

## Subsequent larger-cap proposal diagnostic

E15's source frames reveal the precise colour-proposal bottleneck: while its yellow stone crosses the early right-view ice, the visible yellow contour measures roughly **126–175 px²** in multiple 1 Hz samples, above the previous 120 px² ceiling. The [post-score larger-cap lane](right-large-cap-postscore.json) raises only that ceiling to 180 px², retaining the two-second global assignment and late-seed span rule. It yields 37 raw tracks and 18 directional review paths. All 18 were rendered in four [source sheets](right-large-cap-source-review/manifest.json), then [classified from the sampled pixels](right-large-cap-source-review/source-prefix-classes.json) before context scores were calculated.

The new E15 path A032 visibly follows the yellow stone at 2607, 2609 and 2611 s; its inferred early-ice passage is at 2608.647 s. This removes the colour-observation gap that had split the earlier tracker. The [reproducible same-colour passage audit](right-large-cap-coarse-overlap-postscore.json) now overlaps **17 of 17** earlier coarse windows, one proposal per window. The first four long positive-y paths contain stone pixels but have uncertain physical identity, so this is conditional proposal overlap, **not** 17/17 verified throw recall.

| Source-visible proposed prefix | Clear context | Cluttered review |
| --- | ---: | ---: |
| Short moving-stone path | 13 | 0 |
| Stone pixels, long-track identity uncertain | 3 | 1 |
| Person / wheelchair | 0 | 1 |

The [paired context scores](right-large-cap-combined-context-postscore.json) keep A032 clear (ring non-ice fraction 0.0246; underpoint 0.0000) and flag the person path A037 (0.5499 and 0.9638). The same-agent three-frame classes cannot prove complete deliveries, and neither the cap rule nor context gate establishes event precision or F1. The cap-size change was chosen **after** seeing E15; the unchanged-rule Italy check is [predeclared separately](../canada-italy/RIGHT-LARGE-CAP-TRANSFER-PLAN.md).

The [full-timeline evidence overlay](right-large-cap-full-timeline-overlay.json) preserves all 18 right paths beside the existing 128-event provisional match timeline. Thirteen short source-reviewed stone paths have a unique same-colour left event 0–20 seconds earlier; A032 conditionally pairs with left event R01-S59 at 2598.99 s. The four long identity-uncertain paths and one person path stay explicit review items, leaving the first four left events in this interval without a short right link. This overlay does not alter the original timeline or certify physical cross-view identity.

## Moving-tail extraction from stationary-plus-moving tracks

The first four positive-y right tracks contain a long nearly stationary colour prefix followed by a visibly moving stone. The original seed rule chose the first valid point, so each review path spanned 20 s and its physical identity was uncertain. A [post-score moving-tail derivative](right-large-cap-motion-tail-postscore.json) keeps the same raw observations and all 18 proposal IDs but selects the latest sustained ≥60 px motion over at most 5 s for prefixes longer than 10 s. It shortens A001/A003/A006/A007 to **2–3 s** source-visible stone tails. All changed tails were inspected in the new [source sheet](right-large-cap-motion-tail-source-review/sheet-01.jpg); the other three sheets are byte-identical to those previously reviewed. The [updated source classes](right-large-cap-motion-tail-source-review/source-prefix-classes.json) describe moving stone pixels on the **short tails**, not identity continuity with the earlier stationary part.

The [paired context scores](right-large-cap-motion-tail-combined-context-postscore.json) leave 17/17 short stone tails clear and flag the one person path. The [coarse-window audit](right-large-cap-motion-tail-coarse-overlap-postscore.json) still shows 17/17 conditional stone-pixel overlap. A direction-aware [full-timeline overlay](right-large-cap-motion-tail-timeline-overlay.json) makes **17 unique time/colour links** to the 17 provisional left events in this interval: positive-y right passages precede the first four left passages by about 4.1–4.7 s, and negative-y right passages follow later left passages. This ordering is a development hypothesis about the two delivery directions. These links are neither verified cross-camera stone identities nor independently scored throws; a stationary-to-moving splice can still hide which physical stone moved.
