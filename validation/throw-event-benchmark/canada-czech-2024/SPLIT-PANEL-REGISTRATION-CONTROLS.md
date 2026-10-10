# Quiet-board controls expose foreground-driven camera fits

The [initial split-panel audit](SPLIT-PANEL-REGISTRATION-AUDIT.md) used only
reviewed moving-stone paths. This companion test looks at a deliberately
different development population: adjacent 1 s observations in quiet-tail
partial boards. A pair is eligible when two same-colour proposals are mutual
nearest neighbours, their *conditional* board positions differ by less than
0.05 m, and the next same-colour competitor is at least 0.15 m away. This
produced 4,337 candidate pairs. The frozen sample took the 30 largest raw
pixel displacements of at least 5 px and 30 deterministically spaced pairs
with raw displacement below 1 px. Selection and every measurement are in the
[runner](../../../prototype/scripts/audit_czech_split_panel_board_controls.py)
and the [current result](split-panel-registration-board-controls-edge-guard-v2-development.json).
The [initial result](split-panel-registration-board-controls-development.json)
is retained for comparison. The source, board artifact, runner and registration
code hashes are recorded in each result.

These are **low-drift proposals, not independently verified stationary
stones**. The conditional board positions may share model errors, and a
several-pixel jump may be cap-localization jitter rather than camera motion.
They are nevertheless useful adversarial controls for a camera-motion rule:
a rule should not confidently convert a near-static source-pixel proposal
into a large camera-relative motion cue.

| Result on 60 sampled pairs | Initial registration | Edge-guard registration |
| --- | ---: | ---: |
| Pairs with accepted transform | 60 | 55 |
| Abstentions | 0 | 5 |
| Accepted low-raw (<1 px) pairs with residual >5 px | 2 of 30 | 0 of 27 |
| Accepted high-raw (≥5 px) pairs with residual >5 px | 11 of 30 | 10 of 28 |

Source-frame inspection of S96 at 4043–4044 s shows fixed house markings
while several people move through the left panel. The initial ice-like mask
included moving foreground features and accepted four affine fits, turning
0.369 px raw displacement into a **38.467 px** camera-relative residual.
At S13, 507–508 s, the right panel also appears fixed while players and
equipment move; 0.359 px raw displacement became **6.765 px** residual.
These are concrete examples of why “enough RANSAC inliers” is not sufficient
when foreground objects cover a broad white region.

The current guard compares source-scene edge alignment under the proposed
transform against a no-camera-motion hypothesis. It abstains when a sizable
transform substantially worsens alignment, or when already well-aligned
scene edges give inadequate support to a small shift. The S96 and S13 fits
now abstain. It also abstains on three other sampled controls and nine of
160 pairs on the reviewed moving paths; the latter retain their raw path
observations but have no camera-relative residual. The rule was developed
after inspecting this same 2024 recording, so these numbers are **development
diagnostics**, not an independent transfer result.

The ten remaining high-raw control residuals above 5 px are a material
failure of a standalone 5 px motion gate on these candidate observations.
They may be localization jitter, true residual motion, or identity mistakes;
this audit cannot distinguish them. The next discriminator needs explicit
stone appearance and temporal consistency, plus independently reviewed
stationary and moving source clips. None of these control counts is throw
precision, recall, or F1.
