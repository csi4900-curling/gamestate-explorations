# Left-view proposal-bound transfer check

The [S41 diagnostic](LEFT-BOUND-RECALL-DIAGNOSTIC.md) showed that extending
the left receiving view's lower proposal bound from −6.401 m to −18 m recovers
a source-visible red-stone path. This transfer check replays **the same bound
change and no other rule change** on six other 2024 recordings. Four cases
are selected mechanically: the first positive-y corridor candidate in each
of Slovakia, China, Scotland, and Estonia's existing 1650–2760 s intervals.
Three additional cases (Scotland S11, Italy S07, Latvia S07) were selected
because prior audits marked them unsupported. The exposed full-match controls
are S40 and the two source-reviewed false-positive contexts S96/S143.

| Recording / candidate | Same-colour proposals, original → extended | Original selection → extended selection | Path samples, original → extended |
| --- | ---: | --- | ---: |
| Canada–Czechia [S40](gap-review/s40-left-world-bound-postscore.json) | 36 → 45 | ambiguous → ambiguous | 0 → 0 |
| Canada–Czechia [S41](gap-review/s41-left-world-bound-postscore.json) | 87 → 102 | no supported path → unique path | 0 → 8 |
| Canada–Czechia [S96](gap-review/s96-left-world-bound-postscore.json), known player path | 37 → 71 | unique path → unique path | 7 → 9 |
| Canada–Czechia [S143](gap-review/s143-left-world-bound-postscore.json), known postgame path | 11 → 19 | unique path → unique path | 10 → 12 |
| Canada–Slovakia [S01](../canada-slovakia-2024/left-bound-s01-transfer-postscore.json) | 18 → 26 | unique path → unique path | 6 → 14 |
| Canada–China [D01](../canada-china-2024/left-bound-d01-transfer-postscore.json) | 18 → 23 | unique path → unique path | 7 → 12 |
| Canada–Scotland [S01](../canada-scotland-2024/left-bound-s01-transfer-postscore.json) | 70 → 76 | unique path → unique path | 10 → 16 |
| Canada–Estonia [D01](../canada-estonia-2024/left-bound-d01-transfer-postscore.json) | 54 → 59 | unique path → unique path | 9 → 14 |
| Canada–Scotland [S11](../canada-scotland-2024/left-bound-s11-transfer-postscore.json), prior unsupported | 45 → 62 | no supported path → no supported path | 0 → 0 |
| Canada–Italy [S07](../canada-italy/left-bound-s07-transfer-postscore.json), prior unsupported | 30 → 37 | no supported path → no supported path | 0 → 0 |
| Canada–Latvia [S07](../canada-latvia-2024/left-bound-s07-transfer-postscore.json), prior unsupported | 31 → 33 | no supported path → no supported path | 0 → 0 |

The original-bound replay for all four Canada–Czechia cases exactly matches
the frozen motion artifact's 24 sample times, per-frame proposal lists, and
selector status. Every replay artifact has 24 paired samples and records
the current runner, source, candidate, calibration, detector, and selector
hashes. The source-visible [S41 path review](gap-review/s41-left-bound-path-frames/s41-path-review.jpg)
supports that one recovered path's stone appearance. The other extended
paths have **not** been source-reviewed here; more samples are not necessarily
better trajectories or additional throws.

The immediate lesson is mixed. Wider coverage fixes S41's proposal cutoff
but does not fix S40's ambiguity, recover the three other selected unsupported
cases, or remove the two known false positives.
Even when the selection status stays the same, the selected path length
changes, so downstream trajectory and board handoffs would need rechecking.
This eleven-case diagnostic is far too small and prediction-selected to
estimate precision, recall, or F1. The frozen detector and its 79-candidate
result remain unchanged. A promotion decision requires full-candidate scans
on other recordings and independent exhaustive throw labels.

A later [complete left-corridor interval comparison](FULL-LEFT-INTERVAL-BOUND-RESULTS.md)
scanned all 32 left candidates across Slovakia, Italy, Estonia, Latvia, and
Scotland. Only Italy S03 and Scotland S02 changed motion-selector status;
both had already appeared in other development-stage evidence, so neither
is an independently measured event recall gain.
