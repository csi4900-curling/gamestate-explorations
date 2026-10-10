# Postscore left short-path development result

The frozen full-match screen remains **79 provisional candidates**. A separate [development branch](LEFT-SHORT-PATH-RESCUE-PLAN.md) preserved all 79 and added **nine** after rerunning the same stone-appearance and shared-path duplicate screen on all 116 corridor IDs. The [new motion artifact](full-match-left-short-path-rescue-postscore.json), [116-row patch audit](full-match-left-short-path-patch-postscore.json), and [88-candidate screen](full-match-left-short-path-screen-postscore.json) preserve source, candidate, model and stage hashes. This is an exposed-recording result, **not a measured recall gain**.

The diagnostic was motivated by a concrete failure: the [held-registration audit](full-match-hold-merged-postscore.json) registered 1443 of 1444 sampled left-view frames directly, yet the original selector found unique paths for only 32 of 60 left-view candidates. The four source-selected cases S125, S127, S133 and S137 showed moving stones whose proposed far-entry paths slowed or settled after roughly 1–2 m. Extending those windows from 12 to 20 s **without threshold changes recovered none**; lowering the minimum forward step alone to 0.15 m while keeping 2 m minimum travel recovered only S127. See the [predeclared diagnostic](LEFT-RECALL-DIAGNOSTIC-PLAN.md) and [four-case output](left-recall-diagnostic/results.json). The fixed `0.3 m / 0.5 s` step and `2 m` travel requirements were therefore jointly censoring short, slow visible paths in this recording.

The development rescue used the existing 12 s proposals, changed only left-view path eligibility to a `0.15 m` minimum step and `1.0 m` minimum travel, and applied it only where the original pipeline had no selected path. It produced nine unique new paths, all of which passed the unchanged patch screen; **no prior acceptance was lost**.

| Candidate | Passage time (s) | Selected visible travel (m, conditional) | Patch samples accepted |
| --- | ---: | ---: | ---: |
| S29 | 875.07 | 2.80 | 3/3 |
| S38 | 1361.18 | 3.28 | 3/3 |
| S40 | 1513.81 | 5.25 | 1/3 |
| S77 | 3162.75 | 1.35 | 3/3 |
| S125 | 5355.75 | 1.40 | 3/3 |
| S127 | 5468.90 | 1.92 | 3/3 |
| S128 | 5520.82 | 1.84 | 3/3 |
| S133 | 5773.62 | 1.24 | 3/3 |
| S137 | 5984.90 | 1.80 | 3/3 |

The [agent source review](left-short-path-source-review/review.json) links one midpoint frame per new path and records a visible coloured stone near the proposed left-view location. S40 has only first-patch support, although its later source frame still shows a yellow stone near the right edge of the left view. These checks are **not independent event labels** and do not verify that a path belongs to the early passage candidate or that every delivered stone was found. The known S143 postgame false positive remains accepted by both screens.

The same short-path rule was then applied without retuning to five other existing 2024 recording intervals (Canada–Slovakia, Italy, Estonia, Latvia, Scotland). Their [cross-recording audit](../../curlobserver-learned-probe/short-path-cross-recording/comparison.json) covers **32 left-view candidates and found zero new paths**. Canada–Slovakia was additionally rerun through its original patch and duplicate screen: all 25 decisions remained identical, with 17 provisional acceptances. These intervals have no exhaustive independent throw labels and have previously been exposed to other detector development, so this checks transport of the rule, not precision or recall. The observed gain is concentrated in the full Canada–Czechia recording.

Before this branch can replace the frozen rule, it needs a predeclared evaluation on different full recordings, including source review of false flags and independent exhaustive throw labels. A robust detector will also need to handle the right-view registration gaps and infer complete event boundaries, which this short-path change does not address.
