# Stable board proposals can be player objects

The [six pre-split quiet-tail boards](PRE-SPLIT-BOARD-RESULTS.md) exposed both
missed stones and stable false objects. The original S40 board omits a yellow
stone that the frame detector actually finds at the end of the tail. A
[stationary-suffix replay](gap-review/pre-split-stationary-suffix-development.json)
of the **saved detections** raises the six-window stable-proposal total from
24 to 26: it recovers the S40 yellow stone after discarding one earlier
position while it was still slowing, but it also adds a red object in S131.
The [S131 source frame](gap-review/board-shape-source-review.jpg) shows that
object is a player's hat. Therefore the suffix rule is a diagnostic, **not a
safe board-detector update**; existing board artifacts are unchanged.

The [source-shape audit](gap-review/pre-split-suffix-shape-diagnostic.json)
redecodes the last observed frame for all 26 suffix-board proposals. It records
the colour-component box, height/width ratio, and nominal grey-body support.
The [eight selected source frames](gap-review/board-shape-source-review.jpg)
show these cases:

| Candidate observation | Source-visible object | Original board? |
| --- | --- | --- |
| S33 V02 | Logo on Canadian player's jersey | Yes |
| S33 V03 | Czech player's red hat | Yes |
| S80 V02 | Logo on Canadian player's jersey | Yes |
| S80 V04 | Czech player's red hat | Yes |
| S84 V02 | Logo on Canadian player's jersey | Yes |
| S90 V02 | Logo on Canadian player's jersey | Yes |
| S90 V03 | Real red stone partly occluded by wheelchair | Yes |
| S131 V04 | Czech player's red hat | Suffix proposal only |

These eight were **selected for suspicious shape**, not sampled randomly; the
table is not a false-positive-rate estimate or an exhaustive audit of all 24
original proposals. It does show why temporal stability alone is insufficient:
people and their clothing can remain in one spot through a quiet tail.
Bounding-box shape is also insufficient. The real S90 V03 stone has a tall
colour component because the wheelchair occludes part of it, similar to some
false hats and logos. The [unchanged appearance-model check](gap-review/pre-split-suffix-patch-diagnostic.json)
rejects both S40's true yellow stone (score −1.158) and S131's false hat
(score −0.962) at the inspected frames, so it does not resolve this pair in
its current form.

For complete game state, the next object verifier needs evidence of the
stone body and ice contact, plus explicit occlusion handling, tested on
different camera poses and held-out recordings. Until then, each board is a
set of **unverified stable proposals**, not a count of physical stones. A
simulation must not treat these positions as a complete board.
