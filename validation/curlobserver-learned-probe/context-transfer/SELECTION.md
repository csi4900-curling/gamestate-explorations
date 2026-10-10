# Frozen development transfer selection

The learned box detector and compact-overlay/local-ice context screen were
developed on Slovakia–USA G02 (3900–4200 s). Its first post-fit context result
was 2/0/0 against two coarse agent-authored windows; this is in-sample and
cannot establish generalization.

Before running the new context screen on other gaps, freeze the exact model and
code below. Score the unchanged probe on Slovakia–USA G01 (900–1200 s), G03
(6000–6300 s), and Sweden–Switzerland G01 (3900–4200 s), using the existing
coarse source-only reference subintervals and the existing zero-tolerance
one-to-one candidate scorer. Report raw and screened temporal and colour-aware
TP/FP/FN separately, preserving all first outputs. These source references
were exposed during earlier experiments; this is development transfer, not an
independent validation or whole-match event-F1 claim.

- Public-box model: `81421342467a0ab8d93f4e08829e5928eefbf98c655b2f3a436493ec002feb63`
- `prototype/stone_patch_detector.py`: `4646c822da130b4761657124421b14cde858e0a171f55ab2d69848c23d1d389f`
- `prototype/learned_gap_confirmation.py`: `58fa082a8eb0eefb62e100fd9ed40a84e15c7fd40b026bbb075f138658b03ab1`
- `prototype/gap_motion_candidates.py`: `15f92761a72e5cb971e13efda56a618fa9bab261bea14210ea291094d94d0b29`
- `prototype/scripts/probe_learned_gap_motion.py`: `4af5db6d1600760110001c1f460d1ab58bc00deabc28d98f980ba6dc8f401655`
- `prototype/scripts/screen_learned_gap_motion.py`: `7e580e06a8e65750be12f90c1f10d8615e674197ebc814476ffffed5c68a612e`

The context rule samples up to five observations per track, compares the
source-specific compact scoreboard patch to the first frame of its gap, and
measures ice in an annulus around each proposed box. It withholds tracks above
0.22 median patch distance or below 0.5 median local-ice fraction, then joins
eligible tracks within 8 s and chooses the largest net displacement. These
parameters were chosen after the G02 failure audit and must remain unchanged
for this transfer.
