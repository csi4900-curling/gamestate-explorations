# Frozen right-view visual cues across 2024 matches

The [Estonia/Italy transfer](right-visual-cue-pair-estonia-italy-development.json) applies the unchanged 0.25 ring/below-point context rule and frozen 2022-trained side-view patch model to all 36 previously source-reviewed global-association right paths in two other 2024 matches. It uses each review's exact three source frames and tracked cap boxes. No model threshold was fitted on Estonia, Italy or Latvia.

| Source-reviewed prefix class | Estonia | Italy | Both cues positive | Cues disagree | Both cues weak |
| --- | ---: | ---: | ---: | ---: | ---: |
| Moving stone pixels | 13 | 15 | 28 | 0 | 0 |
| Person/wheelchair pixels | 1 | 2 | 0 | 0 | 3 |
| Stone pixels, long-track identity uncertain | 3 | 2 | 4 | 1 | 0 |

The same frozen cues behave differently on the [53 selected Latvia prefixes](canada-latvia-2024/full-right-all-proposal-visual-cue-pair-development.json): six of 18 stone-pixel proposals have both cues positive, 12 have disagreement, and none have both weak; 15 of 23 person/equipment proposals have both weak, eight have disagreement, and none have both positive. Latvia's path inventory is a different selection from the Estonia/Italy complete reviewed global-association inventories, and proposal duplicates are correlated, so these ratios cannot be read as cross-match accuracy. They do show that the **cue-pair policy is sensitive to the source and selection**. In particular, the frozen patch model has 10 all-negative stone-pixel prefixes on Latvia despite positive stone prefixes in Estonia and Italy. Stone-cap box size alone does not explain the difference: Italy includes a reviewed 5×4-pixel red cap with three positive patch samples, while some larger Latvia caps are negative.

A [four-case source-frame contrast](canada-latvia-2024/latvia-italy-frozen-patch-contrast/manifest.json) pairs Latvia yellow and red stone misses with Italy yellow and red stone positives at similar image scale. The model's cyan context crop contains the visible stone body in all four cases; the missed Latvia scores are therefore not explained by the stone simply falling outside these selected crops. The handles, body shading, paint and surrounding pixels differ, but four postselected examples cannot isolate which visual factor drives the score. We should test an appearance model with source-diverse training and a genuinely separate match before using patch negatives to reject events.

The frozen cues therefore remain review evidence. Neither a dual-positive prefix nor a weak prefix is a verified delivery or a safe rejection. A physical event benchmark still needs independent full-match labels, including throws the proposal generators miss entirely. For state reconstruction, complete same-stone identity across views and reliable settled boards remain missing.

Reproduce the Estonia/Italy transfer with `feasibility/scripts/python.sh prototype/scripts/transfer_right_visual_cue_pair_estonia_italy.py`, then the selected contrast with `feasibility/scripts/python.sh prototype/scripts/build_latvia_italy_patch_contrast.py`. The exporters check source-video, scan, review, context and model hashes and record all three sample scores per path. They do not modify the underlying proposal or review artifacts.
