# Expanded right-entry extraction: source-diverse development transfer

The Scotland seam audit exposed two near-camera omissions in the frozen
640×360 right-camera colour extractor: it ends at image y=325 and rejects
coloured contours above 120 px². A separate diagnostic extractor reaches
image y=360 and accepts contours through 220 px². The original 1 Hz tracker
and y=250/y≤220 entry triage remain unchanged. This experiment asks how many
*review proposals* that wider extraction adds. It does not accept throws.

| Recording and scored interval | Frozen raw tracks / entry reviews | Expanded raw tracks / entry reviews | Frozen entries time-and-colour paired | Extra expanded reviews |
| --- | ---: | ---: | ---: | ---: |
| [Czechia, 0–6683 s](right-entry-transfer/czech-full-expanded-right-first.json) | 276 / 38 | 291 / 40 | 38/38 | 2 |
| [Italy, 1650–2760 s](right-entry-transfer/italy-1650-2760-expanded-right-first.json) | 30 / 8 | 30 / 9 | 8/8 | 1 |
| [Estonia, 1650–2760 s](right-entry-transfer/estonia-1650-2760-expanded-right-first.json) | 23 / 8 | 24 / 9 | 8/8 | 1 |
| [Latvia left-blind interval, 5015–6670 s](latvia24-full-v1/right-expanded-blind-first.json) | 131 / 8 | 133 / 8 | 8/8 | 0 |

Pairing permits the same colour within three seconds and is only a proposal
comparison. The full scan and selected source strips are source/code-hashed;
the frozen detector artifacts were not modified. The separate postreview
y=235/y≤225 variant has more candidates and is **not** replaced by these
original-tier counts.

The [Czechia extras](right-entry-transfer/czech-full-expanded-novel-source-review/manifest.json)
include E120, a short moving red-stone path at 2620.091 s, and E279, a
red-clad player/wheelchair path at 6268.429 s. E120 has a conditional
same-colour left candidate S63 at 2609.269 s; S63 was already retained by
the left motion/patch stage. E279 is an added false review trigger near an
existing reviewed person path. The frozen underpoint cue, run over all 40
widened Czech entries, places [35 transferred or source-reviewed stone
prefixes in clear-context review and five people/wheelchair prefixes in
cluttered review](right-entry-transfer/czech-full-expanded-underpoint-transfer-v2.json).
Those classes are same-agent development reviews or conditional time/colour
transfers, not independent event labels.

The [Italy E025 source strip](right-entry-transfer/italy-1650-2760-expanded-novel-source-review/manifest.json)
and [Estonia E021 source strip](right-entry-transfer/estonia-1650-2760-expanded-novel-source-review/manifest.json)
each show a moving yellow stone. Their prior same-colour routed left
candidates are R01-S59 at 2582.302 s and 2598.990 s, respectively; the
right-minus-left lags are 7.188 s and 11.856 s. Both are additional right
corroboration, not new physical throw counts. The unchanged underpoint cue
places [Italy E025](right-entry-transfer/italy-1650-2760-expanded-novel-underpoint.json)
and [Estonia E021](right-entry-transfer/estonia-1650-2760-expanded-novel-underpoint.json)
in clear-context review. Estonia's earliest near-camera sample has no usable
underpoint band because the frame crops it.

In Latvia's 1655-second active static-left span, the original eight
stone-led right prefixes remain exactly matched in crossing time after
expansion; two extra raw tracks create **no** additional early-entry review.
Two prefixes begin one source frame earlier. The
[eight expanded source strips](latvia24-full-v1/right-expanded-entry-source-review/manifest.json)
show short moving-stone paths, and the unchanged
[underpoint cue](latvia24-full-v1/right-expanded-blind-underpoint.json)
keeps all eight in clear-context review. These selected frames do not prove
eight distinct physical deliveries. The absence of a ninth entry does not
prove the remaining blind interval is throw-free, especially during scene
occlusion, stone handling, or a camera route change. A wider near-camera ROI
alone has not repaired that detector coverage failure.
The previously saved **bidirectional area-aware** full-match scan already
contains a [red end-five gap candidate](../../canada-latvia-2024/FULL-MATCH-AREA-CANDIDATE-UNION.md#end-five-blind-interval-gap-candidate)
at 5507.968 s. Its omission from the earlier ordered handoff was a fusion
scope gap, not a failure that this wider upward-only ROI could fix.

Across these **exposed intervals**, all 62 frozen entry proposals have a
time/colour match after expansion; four extra review proposals appear. Three
extras are visually stone-led and one follows a player. This is a useful
cross-recording development result for the candidate stage, with an observed
false-positive cost. It cannot measure physical throw recall, precision or F1:
the reviewed extras were selected by the new detector, the source classes
were supplied by its developer, the intervals are not independently labelled
for every throw, and a camera time/colour link does not prove stone identity.
The wider extractor and underpoint cue should remain separate review stages
until an exhaustive independent full-match reference tests them together.
