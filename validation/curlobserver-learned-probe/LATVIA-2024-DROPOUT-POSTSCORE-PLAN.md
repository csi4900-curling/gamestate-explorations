# Latvia conditional dropout rescue: postscore compatibility probe

Apply the already existing conditional cap-dropout rescue unchanged to Latvia's fixed-grid motion evidence. This is **postscore**: Latvia candidates and source frames have been inspected, and it cannot revise the frozen 14-event transfer or produce independent F1. The purpose is to check whether the more general no-path rescue subsumes the separately developed S21 shared-prefix proposal, and whether it creates additional motion paths among the four other frozen abstentions.

Fixed input chain (base gaps / registration hold / source motion):

| Artifact under `validation/curlobserver-learned-probe/` | SHA-256 |
| --- | --- |
| `canada-latvia-2024-fixed-grid-gaps-frozen-first.json` | `78c034d5a870284c731183d68b4d0a873b2faea80fddc004a347c1981a208859` |
| `canada-latvia-2024-fixed-grid-hold-merged-frozen-first.json` | `ef6226e419761c02e4dff0e11dae7f9e9e4f13379a9b67f0032758c7ff9cfe81` |
| `canada-latvia-2024-fixed-grid-motion-merged-frozen-first.json` | `e28f892cb5621185726e5678a8fd322df6742f21af888e5a72b9e25971714726` |

The rescue core SHA-256 is `1e893842e9e57fa0e709cd5fddc375013f722f0fff7a20c7ccea26cbdc532918`; runner SHA-256 is `1b97fac7cf14a74307fefbd0e029e3b2be10b1023a55e8a8607c7cea26cbdc532918`.

Use the runner's fixed parameters: left entry −4.5 m, right entry 11.5 m, far band 2 m, maximum gap 4.1 s, shared-prefix minimum five samples, ≥0.7 of best path and ≥2 m conditional displacement. Preserve all 19 corridor candidate IDs and original decisions. Report rescue statuses and any new paths, then apply the existing frozen three-patch appearance check before discussing a possible event proposal. Do not tune on the output.

## Result after running the fixed probe

The [motion rescue](canada-latvia-2024-conditional-dropout-rescue-postscore.json) preserved the 14 baseline paths, abstained on four candidates, and returned one shared prefix for S21. The unchanged [three-patch check](canada-latvia-2024-conditional-dropout-rescue-patch-postscore.json) scored S21 at −0.39, +0.48, and +1.00; two of three patches passed. The [final rescue screen](canada-latvia-2024-conditional-dropout-rescue-screen-postscore.json) therefore has **15 provisional candidates**: all 14 frozen accepted IDs plus S21. S05, S07, S14, and S22 remain abstentions; timed-path deduplication removes none. S21's support is explicitly `provisional_shared_prefix_and_patch_support`, not a verified complete stone track. The first-transfer screen remains 14 accepted and five abstentions.

The separate [episode-level union](canada-latvia-2024-partial-episode-union-development.json) had already grouped S21 and S22 for review; it is a different, postscore interpretation of the same visible period. The fixed dropout screen accepts **S21 only** and does not verify S22 as the same physical stone. Neither output supplies independent event F1, exact throw boundaries, complete game state, or simulation-ready geometry.
