# Right-view ring plus underpoint review cue

The [Canada–Slovakia transfer](RIGHT-ICE-CONTEXT-TRANSFER-RESULTS.md) showed that a tracked athlete's head can sit in otherwise bright ice: two of three reviewed person paths passed the 0.25 surrounding-ice cue. To measure a different visual property, the [underpoint feature](../../../../prototype/right_track_underpoint_context.py) samples a 40-pixel-wide band from 22 to 60 pixels **below** each 640×360 tracked cap, using the same ice HSV rule. A stone's small body generally ends above that band; a person or wheelchair may continue through it. Missing or heavily cropped bands produce an unavailable observation. Both features use the median of first, passage-nearest and last source frames.

The development review rule sends a prefix to **cluttered review** if either the ring or the underpoint non-ice fraction exceeds 0.25. Otherwise it remains in **clear-context review**. This rule was chosen *after* viewing Slovakia's head-track failures. It does not accept a stone or a throw.

The [paired diagnostic](right-entry-transfer/combined-ring-underpoint-development.json) joins source-reviewed paths and scores by source, review and proposal hashes. It covers **87 selected short prefixes** in six exposed 2024 recordings:

| Source-visible tracked prefix | Clear-context review | Cluttered review | Total |
| --- | ---: | ---: | ---: |
| Moving stone | 73 | 0 | 73 |
| Person, wheelchair or clothing | 0 | 14 | 14 |

The two Slovakia head paths B008 and B033 now go to cluttered review because their median underpoint fractions are 0.589 and 0.568. Slovakia's third person path B016 is caught by the ring instead. A China person path B014 has a clear underpoint band but a cluttered ring; the two cues are complementary on these selected cases. The Czech full right-view review contributes 40 stone and five person paths; Scotland contributes eight stone and three person paths. Italy, Estonia and China contribute 12 selected stone and three person paths together.

This apparent separation is **development fit, not precision, recall or F1**. The underpoint geometry and cutoff were selected in response to exposed failures; the source classes are the detector developer's short-prefix visual reviews; and the selected paths are not an exhaustive list of physical deliveries or even all possible track proposals. Ice markings, a broom or player beneath a real stone, a head against empty ice, camera crop, and identity switches can defeat both cues. The next transfer must freeze these parameters and source-review every proposal in a further recording before scores are inspected. Independent complete-end delivery labels are still needed for event accuracy, followed by validated cross-view identities and post-throw boards before simulation-ready game state.

Reproduction uses [`score_right_underpoint_context.py`](../../../../prototype/scripts/score_right_underpoint_context.py) on the matching source videos and preserved proposal/review artifacts, then [`combine_right_context_diagnostics.py`](../../../../prototype/scripts/combine_right_context_diagnostics.py) to pair it with the previously stored ring scores. Each output contains source and input hashes. The diagnostic is deliberately separate from the accepted-event pipeline.
