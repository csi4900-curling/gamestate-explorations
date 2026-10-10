# S41 left-view proposal-bound diagnostic

The frozen full-match screen abstains on S41 at 1590.967 s even though the
[source frames](gap-review/s41-1588-1602-1s.jpg) show a red stone traversing
the left panel. The original [motion artifact](full-match-motion-merged-postscore.json)
registers all 24 candidate-window frames but selects no far-entry path.

The left receiving view's configured `world_bounds` begins at **−6.401 m**.
For the visible stone, the registered image projection is substantially beyond
that bound while it approaches the house. The [isolated replay](gap-review/s41-left-world-bound-postscore.json)
keeps the same video, calibration, registration, body/cap detector, 0.5 s
sampling, and path selector, and changes only that lower proposal bound to
**−18 m**. Results:

The replay's original-bound case exactly reproduces the 24 sample times,
per-frame proposal lists, and selector status in the full-match motion artifact.

| Case | Same-colour proposals in 24 samples | Path selection |
| --- | ---: | --- |
| Original bound | 87 | `no_supported_far_entry_motion_path` |
| Extended bound | 102 | `provisional_unique_far_entry_motion_path` |

The extended path has **eight observations from 1593.5 to 1597.0 s**. Its
[three marked source frames](gap-review/s41-left-bound-path-frames/s41-path-review.jpg)
show the selector following the moving red stone, rather than a player.
Some earlier frames remain rejected by the existing nominal-width check;
extending the bound does not make every distant observation usable. The
projected positions beyond the original calibration footprint have **no
independent metric accuracy validation** and must not be treated as a precise
full-ice trajectory.

The same isolated replay on S40 produces `ambiguous_far_entry_motion_paths`
with both [original and extended bounds](gap-review/s40-left-world-bound-postscore.json).
This is a different failure: its shared stone-like prefix branches into
alternative paths after 1520.0 s. A proposal-bound extension alone does not
solve that ambiguity.

This is an **exposed-match development finding**, not a frozen pipeline update
or a measured F1 gain. Before adopting the wider bound, run the unchanged
setting over other full matches and camera poses, inspect new accepted paths
for player/graphic false positives, and score against independent exhaustive
throw labels. The [replay script](../../../prototype/scripts/probe_left_world_bound.py)
and JSON preserve source, calibration, detector, selector, and runner hashes.
An initial [eleven-case transfer check](LEFT-BOUND-TRANSFER.md) found the S41
gain, no recovery of three other selected unsupported cases, and persistent
false-positive paths in S96/S143; it does not replace full-match validation.
