# Frozen first transfer result

The experimental 2024 split-screen rule was frozen before source inspection and
inference in `SELECTION.md`. The source-only 5-second contact sheets yielded 17
coarse delivery windows, hashed before inference. Against them, the frozen
first pass scored **13 TP / 0 FP / 4 FN** (precision 1.00, recall 0.765,
F1 0.867), below the 0.95 precision/recall acceptance target. These are
partial-match, same-production, agent-blind still-sheet measurements, not
independent full-video validation.

The four missed reference windows are E02, E03, E04 and E16. The first three
did produce correctly coloured passage candidates at 1762.5, 1884.5 and
1946.3 s, inside the blind windows. Their positive-y image speeds were
13.9, 14.6 and 13.6 px/s, just under the development-fitted 14.8 px/s
threshold, so the confirmation rule withheld them. The static pixel-speed
cutoff was therefore an unjustified recall loss across matches.

E16 produced no raw passage candidate. Post-score one-second source review
shows a genuine red stone around 2661–2664 s moving toward the far end.
The red-cap candidate first becomes visible around y=53 in the normalized
left-panel ROI, already beyond both y=60 and y=80 crossing lines. This is the
same fixed-line entry problem observed on Canada–China, now in the opposite
travel direction. The first-pass predictions, score and source-only reference
remain unchanged. Any remedy tested here is post-score development work.

A post-score line-independent tracker now emits a candidate after a coloured
object travels at least 24 px through the early left-panel ROI, even if the
track starts beyond y=60 or y=80. It recovers E16 at 2662.4 s from 13 observed
points spanning 24 px. After the unchanged x=160±60 corridor, it finds all 17
coarse Estonia windows but adds five unmatched candidates: **17/5/0**
(precision 0.773, recall 1.00, F1 0.872). This is development data, not a
second independent transfer score. Equivalent post-score results are 18/7/0
for Canada–China and 17/7/0 for Canada–Italy. The line-free motion evidence
fixes the documented entry/recall failure but does not yet solve player,
changeover and fragmented-track false events.

A later frame-motion context measurement counts changed grayscale pixels around
each observed track midpoint over a ±0.25 s bracket. On these three exposed
intervals, genuine passages had compact motion while most false candidates
involved larger surrounding movement. A cutoff at 1250 changed pixels in an
80×80 box, combined with a 10 s same-colour/direction fragment screen, fits
all 52 coarse development windows with no extras (18/0/0 China, 17/0/0 Italy,
17/0/0 Estonia). **This is an in-sample fit**, because the cutoff was selected
after inspecting these recordings. The rule and code hashes were frozen before
Canada–USA 2024 was downloaded or viewed for the next transfer check.
