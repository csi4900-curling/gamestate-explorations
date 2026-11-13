# Canada–Estonia 2024 receiving-motion transfer

**Frozen transfer outcome: high precision, poor recall.** The Canada–China two-cue filter, fixed in the [pre-transfer plan](CANADA-ESTONIA-2024-MOTION-TRANSFER-PLAN.md), retained only 6 of Estonia's 17 coarse throw windows: **6 TP / 0 FP / 11 FN; precision 1.00, recall 0.353, F1 0.522**. It cannot presently serve as a robust cross-recording throw-event filter. The candidate generator itself had found all 17 windows but also five extras. Filtering lost most real events.

This is a 1650–2760 s interval of a 2024 Canada–Estonia match, not a full-match or unseen-end test. The candidate set and coarse, same-agent source-only reference were already exposed. The separate 1920×1080 video copy has SHA-256 `eaa88f73b56ea982808468a642ad5481428e758881f41cfaf812be58f949a533`; a [motion-rich frame alignment check](canada-estonia-2024-highres-alignment-motion-rich-development.json) selected zero time adjustment at six sampled source times. The reserved Canada–USA unseen end was not used.

| Stage | Candidates retained | TP | FP | FN | Precision | Recall | F1 | Interpretation |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Existing passage candidates | 22 | 17 | 5 | 0 | 0.773 | 1.000 | 0.872 | Already exposed postscore baseline |
| **Frozen China-developed motion + cap patch** | **6** | **6** | **0** | **11** | **1.000** | **0.353** | **0.522** | Actual fixed-rule cross-recording transfer |
| Borrow a camera transform during a verified still shot | 16 | 15 | 1 | 2 | 0.938 | 0.882 | 0.909 | Postscore repair |
| Also permit bounded unobserved path gaps | 18 | 17 | 1 | 0 | 0.944 | 1.000 | 0.971 | Postscore repair |
| Also remove a shared timed motion path | 17 | 17 | 0 | 0 | 1.000 | 1.000 | 1.000 | Postscore fit to exposed match |
| Final motion + patch + duplicate screen | 17 | 17 | 0 | 0 | 1.000 | 1.000 | 1.000 | Postscore fit; **not transfer validation** |

The [stage score artifact](canada-estonia-2024-motion-stage-scores-development.json) records selected candidate IDs, exact input hashes, and the same scorer for every row. The frozen [motion](canada-estonia-2024-candidate-centric-motion-development.json), [patch](canada-estonia-2024-candidate-motion-patch-appearance-development.json), [screen](canada-estonia-2024-candidate-motion-patch-screen-development.json), and [score](canada-estonia-2024-candidate-motion-patch-score-development.json) artifacts remain unchanged. Frozen versions of the later-edited motion selector and patch runner are preserved as [motion selector](stone-proposal-path-frozen-transfer.py) and [patch runner](audit-candidate-patch-frozen-transfer.py).

## What failed

The candidate-centric scan sought a same-colour, far-to-house moving stone in the expected receiving camera during a 12 s lookahead, sampled every 0.5 s. It required a registered image and a unique path. Only six of 22 passages got a path. In later right-view shots, many frames failed SIFT registration because too few spatially distributed matches survived, even while the lower ice and camera position remained similar. The [right-view contact sheet](canada-estonia-2024-right-view-failure-contact-development.jpg) shows the failure cases. This is a registration/coverage failure in the filter, not evidence that the 11 real throws were absent.

The first repair explicitly reused the nearest accepted transform within 10 s **only when** lower-ice image similarity supported a still camera; 199 previously rejected samples used such a transform. It raised unique-path coverage to 16. Two remaining true paths, S17 and S20, were interrupted by registration-abstention samples. A separate bounded-gap selector recovered S17 across a largest 2.0 s observation gap and S20 across a 4.0 s gap. These intervals remain unobserved; the selector does not prove continuous stone identity or physical accuracy.

The remaining extra candidate S24 shared nine identical timed projected observations with S23, a true yellow path. The [deduplication artifact](canada-estonia-2024-candidate-shared-motion-dedup-development.json) retains one event for this shared path. Appearance scores are positive for both S23 and S24, so the cap-patch cue alone does not resolve duplicate event fragments. The [post-repair patch artifact](canada-estonia-2024-candidate-motion-patch-after-hold-development.json) and [final screen](canada-estonia-2024-candidate-motion-patch-after-hold-screen-development.json) document that limitation.

## What this supports next

The repair suggests a better architecture: preserve high-recall passage candidates, use camera-shot-aware registration to collect receiving motion, allow explicitly bounded missing observations, check stone appearance, then collapse candidates supported by the same timed path. **Its apparent perfect score is an in-sample fit after inspecting Estonia's errors.** Before claiming transfer or high F1, freeze these rules and run them unchanged on a different recording with independently marked throw windows, reporting both candidate-generation recall and filtered precision/recall. Coarse windows also do not measure exact release or settle time.

No stage here verifies complete stone identity, settled board state, metric trajectory accuracy, or simulation-ready game state. Those remain separate requirements after event segmentation.

A later [conditional cap-dropout rescue](CANDIDATE-DROPOUT-RESCUE-DEVELOPMENT.md) also fits this already exposed interval at 17/0/0. It does not alter the frozen 6/0/11 cross-recording result.

Reproduce the stage table from the repository root with a new output path (the script preserves existing artifacts):

```sh
feasibility/scripts/python.sh prototype/scripts/score_estonia_motion_stages.py \
  --candidates validation/throw-event-benchmark/canada-estonia-2024/development-span-corridor.json \
  --frozen-screen validation/curlobserver-learned-probe/canada-estonia-2024-candidate-motion-patch-screen-development.json \
  --hold validation/curlobserver-learned-probe/canada-estonia-2024-candidate-registration-hold-development.json \
  --gaps validation/curlobserver-learned-probe/canada-estonia-2024-candidate-motion-with-gaps-v2-development.json \
  --dedup validation/curlobserver-learned-probe/canada-estonia-2024-candidate-shared-motion-dedup-development.json \
  --postscore-screen validation/curlobserver-learned-probe/canada-estonia-2024-candidate-motion-patch-after-hold-screen-development.json \
  --reference validation/throw-event-benchmark/canada-estonia-2024/blind-reference.json \
  --output /tmp/estonia-motion-stage-scores-check.json
```
