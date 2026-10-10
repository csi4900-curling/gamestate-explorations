# Fixed area-aware right-view transfer on Canada–Italy 2024

The [predeclared plan](RIGHT-AREA-AWARE-TRANSFER-PLAN.md) froze the Canada–USA-developed area-aware association, late-seed proposal, 1650–2760 s source interval and the paired 0.25 context review thresholds before this Italy run. Italy had been used for earlier detector development, so this is an **unchanged-rule development transfer**, not an independent event evaluation.

The [full interval probe](right-area-aware-fixed-transfer.json) preserved 36 raw tracklets and emitted **17 review paths**. All 17 were displayed in four [source strips](right-area-aware-fixed-source-review/manifest.json); [same-agent source classes](right-area-aware-fixed-source-review/source-prefix-classes.json) were saved before context scoring. Thirteen paths visibly follow short moving-stone motion, two contain stone pixels along long raw prefixes whose same-colour identity remains uncertain, and two follow people/wheelchair clothing or equipment.

| Source-visible proposed prefix | Clear context | Cluttered review |
| --- | ---: | ---: |
| Short moving-stone path | 13 | 0 |
| Stone pixels, long-track identity uncertain | 2 | 0 |
| Person / wheelchair | 0 | 2 |

The [paired ring and underpoint score](right-area-aware-combined-context-transfer.json) uses the frozen rule and retains all proposals. A006 is cluttered in both features; A007 has a clear surrounding ring but a cluttered below-point band. No short stone path is sent to cluttered review in this selected proposal set. The two long-track stone-pixel paths remain identity-uncertain despite clear context.

Against the earlier same-agent [17-window coarse reference](blind-reference.json), the 15 stone-pixel paths occupy **15 distinct same-colour windows**. The old bidirectional proposal overlapped 13 of those 17 windows; the revised tracker adds I02 and I10, while I04 and I16 remain without a source-reviewed right stone path. This is conditional coarse-window overlap, not physical throw recall or F1. It does show that the Canada–USA association change transfers some additional source-visible stone motion without retuning on Italy, while leaving a real proposal-coverage gap.

The next test must inspect I04/I16 and replay the unchanged association across further recordings and view layouts. Before game-state or simulation use, short-path identity, cross-camera links and post-throw settled boards still need validation; independently labelled complete ends remain necessary for event accuracy.

## Post-score two-second-gap diagnostic

The [I04/I16 source sheet](right-missing-i04-i16-postscore.jpg) confirms that the right camera shows moving red stones in both missing coarse windows. The 1 Hz colour observations in I04 contain a red stone at y≈300, 275, 256, then 222 with **one missing second**; I16 contains y≈299, 266, then 214 with a similar one-frame hole. The fixed one-second track linker stops at those holes. A focused replay with a two-second observation gap connects each short stone path without changing the colour mask or 40 px/s speed limit.

The separate [full-interval gap-two probe](right-area-aware-gap2-postscore.json) was chosen *after* seeing Italy's misses. It emits 19 proposals. All 19 appear in four [source strips](right-area-aware-gap2-source-review/manifest.json) and were [source-classed](right-area-aware-gap2-source-review/source-prefix-classes.json) before their context scores:

| Source-visible proposed prefix | Clear context | Cluttered review |
| --- | ---: | ---: |
| Short moving-stone path | 14 | 0 |
| Stone pixels, long-track identity uncertain | 2 | 1 |
| Person / wheelchair | 0 | 2 |

The [paired gap-two context result](right-area-aware-gap2-combined-context-postscore.json) still flags both people. Its new I04 and I16 proposals show short moving-stone paths. But A028, in I13, appears to join an early yellow component to a later moving yellow stone across a two-second gap; it is identity-uncertain, despite the earlier one-second variant's clearer short path there. Thus the post-score gap change raises coarse-window stone-pixel overlap from 15/17 to **17/17** while increasing long-track identity uncertainty from two to three paths. It is an in-sample tradeoff, not a robust throw-recall result. The gap-two variant must transfer unchanged to another recording before it is considered for the review pipeline.
