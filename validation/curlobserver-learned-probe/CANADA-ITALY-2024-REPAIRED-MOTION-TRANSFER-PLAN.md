# Frozen repaired-motion transfer plan: Canada–Italy 2024

Recorded 8 October 2026 **before obtaining or inspecting a 1080p Italy interval copy and before running the repaired candidate-centric receiver screen on it**. This is a third recording from the same 2024 production, but its 360p source, candidate set, and coarse same-agent reference have already been exposed. It is a fixed-rule **development transfer**, not an untouched or independently labelled benchmark. The reserved Canada–USA unseen end stays untouched.

Use `validation/throw-event-benchmark/canada-italy/development-span-corridor.json` (SHA-256 `10b4166a2275ced86d4fa4c8d4395a42a46e83aa36430567b60d0aab1bd5fa5d`), all 24 candidates over source time 1650–2760 s. Do not remove or relabel candidates. Score only after inference against `blind-reference.json` (SHA-256 `a5886533fc79905a89efb913491b71262f3550a8b83239bf5f9d413a9ed5fb28`), 17 coarse windows. Keep the original candidate baseline, fixed-rule output, and score separate.

Download the separate 1920×1080 video interval for source `Vp3TIdOAlrc`, then verify its source-time alignment against the existing full-match 360p file before inference. Run the same candidate-centric scan with source offset 1650 s, 12 s lookahead, 0.5 s sampling, and 160 px maximum corner displacement. Apply the Estonia-developed still-shot registration hold (nearest valid anchor within 10 s, lower-ice similarity unchanged), the bounded gap selector (maximum 4.1 s and skip only `abstained_no_stable_anchor` samples), the frozen cap-patch model (positive on at least one first/middle/last point), and shared timed-path deduplication unchanged. Preserve each intermediate artifact. Do not inspect the Italy reference or tune thresholds after the first 1080p inference and before recording the fixed-rule score. If the video or calibration differs, record the failure as such rather than silently changing the rule.

Frozen code/model fingerprints:

| Item | SHA-256 |
| --- | --- |
| Candidate-centric runner | `77f9618344b41e773121e0348215206ecb7b6989fe7239f840e120428f612714` |
| Motion selector | `8cae87a9b90904647ccb67cceec2473739ccf1d626b68e1305769b28107d63cd` |
| Registration-hold runner | `10dc284a12da5858c4443339dabd65e53e197a9bd9a96df7208931e23542cc32` |
| Lower-ice similarity | `89d8ec83d1e259dd12fd3b9e50e7bdb6ba95820866a93a16e99f9ac7a277a59e` |
| Gap-selection runner | `45ecb222ef75899326febfbae8a0e1c6aed5d3ffad04bf60408787e22a891b8c` |
| Timed-path dedup core | `e43acfc10db0d0e4deaff578887244cbe51e1d08a2e7d7be8f44ad81bdde0c31` |
| Timed-path dedup runner | `2f05c912ecb0ee0a434ef128f86cd04d7ae90416845d840f4148c856bb1d25a0` |
| Patch-audit runner | `716ae811e64566044b729883cb051bd757a8a1a8e7f5564b76b08ea72ae1c17d` |
| Two-cue screen core | `4689d5cc657736417fe73404a4fec5faec0392cdb7cd6b28f3a12e95c560a52f` |
| Final screen runner | `94c981a02b8c9ade9ebeea9e49baf6b144e9a9f59ab8d3de69ea49f0afeb5cfd` |
| Cap-patch model | `10036a8b13e7e35f0be3cfd7280e9e0afaa3cf5b5da6cecc5623fb79695e0670` |

This test can reveal whether the repaired filter survives one more same-production recording. It cannot prove full-match exhaustiveness, cross-camera-family robustness, exact release or settle time, physical stone identity, complete game state, or simulation readiness.

The fixed-rule [transfer result](CANADA-ITALY-2024-REPAIRED-MOTION-TRANSFER-RESULTS.md) is 14 TP / 0 FP / 3 FN against the exposed coarse windows; diagnosis and any subsequent changes are postscore work.
