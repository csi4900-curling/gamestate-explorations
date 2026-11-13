# Canada–USA 2024 right-view context transfer and recall audit

The [predeclared plan](RIGHT-CONTEXT-TRANSFER-PLAN.md) fixed a 1650–2760 s full-video interval, the 1 Hz 40 px/s bidirectional right-colour proposal, and the 0.25 ring-or-underpoint review tier before this recording's new right proposals were inspected. The video had already been used for a different left-view detector and a source-only coarse reference, so this is **same-production development transfer**, not unseen independent validation.

The [frozen right probe](right-bidirectional-context-transfer.json) preserved 66 raw colour tracks and emitted **16 short review proposals**. Every path appears in the four [source sheets](right-bidirectional-context-source-review/manifest.json), and [same-agent source classes](right-bidirectional-context-source-review/source-prefix-classes.json) were saved before either context score. Fifteen paths visibly follow moving stones; B064 follows a wheelchair athlete.

| Source-visible short path | Clear context | Cluttered review | Total |
| --- | ---: | ---: | ---: |
| Moving stone | 15 | 0 | 15 |
| Person / wheelchair | 0 | 1 | 1 |

The [combined result](right-combined-context-transfer.json) uses the frozen ring and below-point thresholds. B064 is flagged by the surrounding ring; its below-point band alone remains clear. This transfer adds no missed stone paths to cluttered review, but 15 stones and one person are too few and too selected to validate a classifier.

## Proposal coverage, before and after a post-score fallback

The 15 short stone paths fall in **15 distinct** windows of the earlier 20-window [source-only coarse reference](blind-reference.json). The missing windows are U02, U03, U04, U08 and U09. This is conditional window overlap, **not physical throw recall**. The [post-score source sheet](right-missing-window-postscore.jpg) and preserved raw tracks show why the original proposal stage missed several visible paths:

- U03's yellow raw track B009 is long and initially almost stationary. The 60-pixel movement starts too late relative to the track's first point for the original 20-second rule.
- U04's red raw track B015 starts with a tall narrow colour component, which fails the original first-cap shape rule. Its later samples switch from stone pixels to a player's clothing.
- U08 B032 and U09 B034 have initial cap areas of 10 px², below the fixed 12 px² seed minimum, although later observations show moving stones.
- U02 has no same-colour raw track with a 60-pixel short span in this scan. The sparse source sheet shows a visible red stone early, but does not establish why its motion was not maintained as one track.

The separate [late-seed diagnostic](right-late-seed-postscore-development.json) searches later valid starting points in each preserved raw track without changing or deleting the 16 original proposals. It is **post-score development**, designed after inspecting those five misses. It emits seven additional review paths. All seven were [rendered](right-late-seed-source-review/manifest.json) and [source-reviewed](right-late-seed-source-review/source-prefix-classes.json) before their context scores:

| New late-seed path class | Clear context | Cluttered review |
| --- | ---: | ---: |
| Clear moving-stone pixels (B032, B034; U08, U09) | 2 | 0 |
| Stone pixels, same-colour identity uncertain (B009; U03) | 1 | 0 |
| Stone-to-player identity switch (B015; U04) | 0 | 1 |
| Person / wheelchair (B021, B022, B024) | 0 | 3 |

The [late-seed context result](right-late-seed-combined-context-postscore.json) separates these sampled source classes, but it cannot repair B009's identity uncertainty. Thus source review demonstrates **17 distinct coarse windows with a clear short stone path**, one more with stone pixels on an identity-uncertain long path, and two without a trustworthy short stone path from this right scan. None is promoted to an accepted delivery. The original left-view frozen detector's 20-window result cannot be transferred to this right-view candidate, and the context cue cannot recover a throw that the proposal stage never emits.

The next high-recall work is to start new short tracks when a raw track changes object or resumes motion, recover small first caps without treating clothing as stone, and preserve unresolved windows for cross-view evidence. Every added path still needs source identity review; independently labelled complete ends remain necessary for event precision, recall and F1. Game-state and simulation outputs require additional post-throw board and geometry validation.

## Subsequent area-aware association diagnostic

The post-score inspection found a more precise cause for U02 and U04. At U02, the red stone cap moves from about y=208 at 1704 s to y=231, 262 and 296 over the next three samples. The original greedy linker attaches its older track to a *nearer small stationary red blob* at y≈190 instead of the moving stone. At U04, the stone cap moves from about y=220 at 1810 s to y=254 and 290, while the linker again selects smaller person-associated red pixels nearby. The resulting 2–3-frame stone fragments are discarded by the original four-observation track rule. This is a data-association failure, not proof that the video lacks the moving stone.

The separate [area-aware diagnostic](right-area-aware-postscore-development.json) adds a penalty for abrupt coloured-cap area changes when linking consecutive observations, retains three-observation moving tracklets, and permits the later valid seed described above. Its area-change weight and tracklet length were set *after* inspecting U02/U04, so this is in-sample development. The full 1650–2760 s replay preserves 83 raw tracklets and emits **25 right-view review proposals**. All 25 were shown in five [source sheets](right-area-aware-source-review/manifest.json) and [classified from source pixels](right-area-aware-source-review/source-prefix-classes.json) before context scoring:

| Source-visible proposal class | Clear context | Cluttered review |
| --- | ---: | ---: |
| Short moving-stone path | 17 | 0 |
| Stone pixels on a long, identity-uncertain path | 3 | 0 |
| Person / wheelchair | 0 | 5 |

The [paired context output](right-area-aware-combined-context-postscore.json) again separates these *reviewed proposals*, but clear context does not resolve the three same-colour identity uncertainties. The 25 proposals place source-visible stone pixels inside **all 20** earlier coarse windows, one per window; U02, U03 and U04 are the identity-uncertain cases. That is conditional overlap with a same-agent coarse reference after fitting on this recording. It is **not** a 20/20 physical throw-recall result, an independent F1 score, or a reliable generalization claim. The new association and seed rules need an unchanged transfer to a different recording, full source review of new paths, and independent event truth before promotion.
