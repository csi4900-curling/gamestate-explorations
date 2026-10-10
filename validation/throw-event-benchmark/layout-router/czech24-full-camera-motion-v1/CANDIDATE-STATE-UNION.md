# Czech candidate-to-state evidence union

The [source-hashed union](candidate-state-evidence-union-development.json)
connects the current full-match raw/context run to the older receiving-camera
episode and partial-board work without changing any throw decision. It
contains **147 current left raw proposals** (96 context-confirmed and 51
retained for review) and **23 historical right-only episode proposals**:
170 ordered evidence rows, **not** 170 physical throws. The historical
handoff covers 116 of the current left IDs, leaving 31 left raw proposals
without an old episode. Raw candidate ID, time, and colour lists are exactly
equal across the current and historical full-match runs.

The union points to **66 distinct historical episodes with a stable
partial-board observation**. There are 68 candidate-row references because
some left candidates share an episode. A board reference is attached only
when the old episode's state status is `partial_board_observed`; a record
marked `accepted_event_without_stable_board` carries no board reference.
The historical boards are view-local, conditionally projected observations,
with unverified completeness and stone identities. The union deliberately
does not copy them into a complete post-throw state.

The two [source-reviewed red stones S04 and S13](WITHHELD-STONE-SOURCE-REVIEW.md)
illustrate the handoff. Both remain `needs_review` under the simple context
gate, have optional dual-observer support, and point to historical episodes
E003 and E011 with partial boards. Known non-stone raw path S96 remains
`needs_review`, lacks dual-observer support, and points to E088, whose old
screen provisionally accepted it but whose status is
`accepted_event_without_stable_board`. None of these evidence combinations
proves a distinct physical delivery or the identity of the stone in a later
board.

The [path-to-board gap audit](RESCUED-STONE-BOARD-GAP.md) makes that missing
identity link concrete: S04's selected receiving path stops at 200.0 s,
before any red board observation; S13's stops at 499.0 s, six seconds before
its red board observation. Neighboring S13 partial boards show a red change
while two yellow observations remain locally stable, but the red identity
through the intervening motion is not observed.

Every union row therefore leaves release time, settle time, delivered-stone
identity, complete board, metric trajectory, spin count, and simulation
readiness unknown. Before generating a coaching replay from a row, the system
must establish physical event identity across views, identify the delivered
stone among persistent board objects, verify that the board is settled and
complete, and validate the rink-coordinate projection. The union makes
those missing links explicit while allowing event and board evidence to be
reviewed together.

Reproduce with
`python prototype/scripts/build_czech_candidate_state_union.py` after
moving its output JSON aside. The exporter verifies all 147 raw IDs across
the current and historical sources and pins every input and its own code by
SHA-256.
