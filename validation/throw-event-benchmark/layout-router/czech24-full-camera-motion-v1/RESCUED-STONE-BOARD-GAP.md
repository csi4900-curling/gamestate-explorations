# What remains between a rescued stone path and a board state

The [reproducible S04/S13 audit](rescued-stone-path-to-board-gap-development.json)
joins the source-reviewed left passages, their historical receiving-camera
motion paths, and neighboring partial-board episodes. It uses the existing
conservative same-colour board comparison and every raw passage candidate as
an intervening-event check.

| Candidate | Selected receiving motion | First same-colour board observation | Minimum unobserved interval | Neighboring-board result |
| --- | ---: | ---: | ---: | --- |
| S04 | 197.0–200.0 s | red V01 at 204.0 s; red V02 at 212.0 s | 4.0 s | Previous board unavailable; next comparison has intervening S05 |
| S13 | 492.5–499.0 s | red V01 at 505.0 s | 6.0 s | Same-view partial comparisons available before and after |

For S04, the nearest historical episode before it has no stable board, and
the raw candidate S03 sits between that episode and S04. The next episode
cannot be compared directly either because S05 is an intervening raw
passage. S04's board has two red observations, both with unknown persistent
identity. Although the moving red stone is visible in both source-camera
panels, the selected receiving path ends before either board observation.

For S13, the previous and next partial boards are both in the right view,
with no intervening raw passage between each adjacent pair. Two yellow
observations match locally across the previous→S13 comparison at 0.0067 m
and 0.0033 m in conditional coordinates, and across S13→next at 0.0057 m
and 0.0020 m. The red observation from before S13 has **no nearby match** in
S13's board; S13's red observation has no nearby match in the next board.
That is an observed board change, not a verified addition/removal or proof
that the tracked delivered stone became red V01. The selected path still
ends six seconds before red V01's first stable observation.

That six-second interval is the gap in the **frozen selected motion path**.
A later [fragment-aware cap-continuation probe](../../canada-czech-2024/FRAGMENT-AWARE-CAP-CONTINUATION.md)
reaches the first red board frame at 505.0 s after merging a small split
handle fragment at 502.0 s. Its cap ends 0.959 image pixels from the board
cap, but another red stone is close near 501 s; the probe remains a local
image-continuity hypothesis, not a verified delivered-stone identity.

The gap to close is a continuous, same-stone observation from moving path
through the collision/settling interval into a board object, with explicit
handling of occlusion and same-colour stones. The board detector must also
establish completeness and metric accuracy before these observations can
drive a physical simulation. Neither candidate currently has a verified
release time, settle time, delivered-stone board identity, or simulation-ready
state.

Reproduce with
`python prototype/scripts/audit_czech_rescued_stone_board_gap.py` after
moving its output JSON aside. The artifact pins the current raw proposals,
state union, historical motion paths, historical board episodes, and board
comparison code by SHA-256.
