# Third-source frozen visual-gap transfer

The scanner, scene screen, full source interval, three interior gaps and seven
source-only coarse delivery windows were frozen in `SELECTION.md` before either
candidate stage ran. The scored intervals exclude two boundary portions where
a stone was already moving when an unsupported span began.

| Candidate stage | TP | FP | FN | Precision | Recall | F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Raw visual tracks | 5 | 15 | 2 | 0.250 | 0.714 | 0.370 |
| Frozen ice-scene/episode screen | 4 | 3 | 3 | 0.571 | 0.571 | 0.571 |

These are **candidate-to-coarse-window** scores, not confirmed throw-event F1
or a whole-match estimate. The first outputs and per-gap score files are
preserved. The full routed recording produced 95 supported-layout events and
five coverage gaps; that count also has no exhaustive full-match reference.

Post-score audit shows several distinct failures. In G01, a yellow visual
track starts at 939 s, before the frozen yellow delivery window begins at
945 s. The one-to-one zero-tolerance scorer therefore records a miss and an
extra, even if later source review associates them; the original score is
unchanged. In G02, the visual scanner emitted no yellow track for the visible
yellow delivery, then the episode screen preferred an earlier red motion
track at 3974 s over the later red delivery track at 3993 s. In G03, camera
changes fragment the red delivery into multiple tracks, one of which remains
an extra after screening. These observations show both detection recall and
episode identity need stronger evidence than local cap motion, global ice
fraction and an eight-second joining gap.

The references were made by the developing agent from five-second source
sheets, with denser sheets for part of G03. They are not independent human
labels and may omit brief or occluded deliveries. The measured result is
nevertheless enough to reject the proposed scene/episode screen as a robust
high-precision, high-recall solution on this transfer.
