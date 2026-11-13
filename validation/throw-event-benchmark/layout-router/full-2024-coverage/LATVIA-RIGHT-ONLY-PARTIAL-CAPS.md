# Latvia right-only post-entry cap observations

This document describes the earlier single-timestamp observation. The later
[runner replay](latvia24-full-v1/right-blind-runner-replay/latvia-right-partial-caps-current.json)
checks both source-frame endpoints of each entry-line crossing bracket. It
retains five partial cap sets, two scene-motion abstentions and one additional
timing-sensitive abstention (R025). The two exports use different entry times;
the earlier six/two count should not be interpreted as robust to that timing
choice.

The current [runner-compatible sequence](latvia24-full-v1/right-blind-runner-replay/latvia-right-board-sequence-current.json)
compares only adjacent right-entry samples and checks the painted house in
normalized source frames. Of seven pairs, three support **conditional image
cap associations** and four abstain because a cap set is unusable. The three
usable comparisons contain 11 matched local cap pairs; their unmatched caps
are visible-proposal changes, not physical stone additions or removals. This
supersedes the four/three count below, which belongs to the earlier
single-timestamp extraction. The [export script](../../../../prototype/scripts/export_right_board_sequence.py)
records video and input hashes and is available through the routed runner's
`--compare-blind-right-boards` flag.

The companion [left-candidate scan](latvia24-full-v1/right-blind-runner-replay/latvia-left-partial-caps-current.json)
now covers **all 119** routed left proposals, including 47 withheld by the
context filter. Its guarded post-candidate right-view samples find 22 partial
stable cap sets, 12 samples with no stable caps, and 85 abstentions (41 next
candidate/route boundary, 20 time-bracket disagreement, 24 scene/player
motion). The [joined handoff](latvia24-full-v1/right-blind-runner-replay/latvia-candidate-state-handoff-v2.json)
therefore has an observation status for all 127 candidates. This is coverage
of the *review ledger*, not coverage or accuracy of physical game states.
The [all-candidate adjacent sequence](latvia24-full-v1/right-blind-runner-replay/latvia-candidate-image-board-sequence-current.json)
has 126 pairs: 10 conditional image comparisons (37 locally matched cap
pairs), 114 missing-usable-cap abstentions, one painted-house alignment
abstention and one origin-change abstention. Neither the 37 associations nor
the unmatched visible caps establish stone identities or physical board
changes.
The [image-house ellipse export](latvia24-full-v1/right-blind-runner-replay/latvia-candidate-house-ellipse-current.json)
finds a stable three-frame painted-house ellipse for **20 of 27** usable cap
observations across both origins. Six abstain because the fitted geometry
changes across samples, and one because paint cannot be fitted in all three.
The resulting 96 cap positions are normalized by the image ellipse axes;
they are not stone contact points or rink metres.

During Canada–Latvia 2024 source seconds **5015–6670**, the left broadcast panel is visually static while the right panel remains active. The camera-aware fusion retains eight source-visible right-entry prefixes as **right-only reviews**, not accepted physical throws. A post-entry image check now records what the right panel shows 15, 20 and 25 seconds after each image-line crossing.

The [observation export](latvia24-full-v1/right-entry-partial-cap-observations.json) finds **six** intervals with coloured-cap blobs repeated near the same right-camera pixel in all three samples. It explicitly abstains for R020 and R028 because large image changes across the sampled house region are consistent with player motion, occlusion, or a changing scene. The [source-only tail strips](latvia24-full-v1/right-entry-board-tail-review/manifest.json) show all 24 sampled frames; the [marked review sheets](latvia24-full-v1/right-entry-partial-cap-review/manifest.json) show the six candidate sets and both abstentions on the middle frames.

| Right entry | Image observation | Repeated red/yellow cap proposals |
| --- | --- | ---: |
| R005 | partial image-cap set | 3 / 1 |
| R008 | partial image-cap set | 4 / 1 |
| R014 | partial image-cap set | 3 / 2 |
| R017 | partial image-cap set | 4 / 2 |
| R020 | abstain: scene or player motion | — |
| R024 | partial image-cap set | 5 / 2 |
| R025 | partial image-cap set | 4 / 3 |
| R028 | abstain: scene or player motion | — |

These are **stable colour-cap proposals, not counted stones**. Nearby stones overlap in the side view; handles can be occluded, and coloured equipment or clothing can yield cap-like blobs. The camera-local pixel coordinates are neither rink metres nor shared across camera views. Counts can fall between rows because visibility changes; no addition, removal, collision, score, settled physical board, or persistent stone identity follows from them. Every row retains `simulation_ready: false` and the raw per-frame candidates so a later reviewer can challenge each proposal.

The fixed extraction uses the existing right-panel colour proposal, a bounded house-area crop, a three-frame same-colour match within five pixels, and a conservative image-change abstention. The [code](../../../../prototype/scripts/export_right_only_partial_caps.py) verifies the source video against the fusion fingerprint. The region and scene threshold were selected on this exposed footage, so these observations are development evidence and cannot validate a general board detector. Independent event labels and a calibrated, occlusion-aware stone model are still needed for complete game-state reconstruction.

## Abstention-aware sequence

The [alignment-gated sequence export](latvia24-full-v1/right-entry-partial-cap-sequence-alignment-gated.json) places all eight right-only entries in time order. Of seven adjacent pairs, **four** have conditional same-colour, nearby pixel associations, totaling **16 local cap pairs**. The other **three** pairs abstain because one side lacks a usable cap set. In particular, no comparison skips across R020's occluded interval to infer a state change between R017 and R024. The [sequence code](../../../../prototype/right_view_cap_sequence.py) accepts only mutually unique positions within five pixels after the sampled painted-house check passes. A nonzero best shift or blue-mask overlap below 0.7 now causes an explicit alignment abstention. All matches remain unverified physical identities; all entries and transitions remain non-simulation-ready. The visible-cap associations cannot establish full camera pose, the same physical end, or a stone addition/removal.

The [source-hashed house-alignment audit](latvia24-full-v1/right-entry-house-alignment.json) checks the painted blue ring at the middle sample of each usable board observation. In all **four** adjacent usable pairs, zero-pixel translation is the best match within an eight-pixel search, with blue-mask overlap of **0.739–0.839**. This supports comparing nearby image positions at those selected instants: the visible house paint has not measurably shifted by an integer pixel under this mask. The audit does not verify full camera pose throughout an event, and the mask is partly occluded by players and stones. The 0.7 overlap cutoff was selected on this exposed recording, so transfer performance remains untested. Run [the audit script](../../../../prototype/scripts/audit_right_only_house_alignment.py) with the source, observation JSON and an unused output path to reproduce it. The older [ungated sequence](latvia24-full-v1/right-entry-partial-cap-sequence.json) is retained for comparison; use the alignment-gated export for downstream work.
