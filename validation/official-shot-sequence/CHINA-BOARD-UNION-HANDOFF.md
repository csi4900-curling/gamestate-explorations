# Provisional China event-to-board handoff

The [source-scoped handoff](china-board-event-union-handoff-development.json) joins the [provisional event union](PROVISIONAL-EVENT-EVIDENCE-UNION.md) to the same eight previously selected China board windows by exact shared delayed-counter ID. Five windows contain partial boards. All five now have one provisional counter-linked event candidate, including B26 and B57, which were absent from the narrower cap-fusion envelope. This is **bookkeeping coverage**, not independent validation: the counter is a shared input to both sides of the join.

| Counter | Video-derived board | Event evidence | Timing relationship |
| --- | --- | --- | --- |
| B25 | 1 visible stone | Existing visual-origin candidate | No comparable travel interval |
| B26 | 1 visible stone | Yellow travel-only candidate in `S124` | Board frames 1620–1624 s overlap the observed travel window 1611.8–1624.4 s |
| B29 | 1 visible stone | Existing visual-origin candidate | No comparable travel interval |
| B57 | 5 visible stones | Red travel candidate in `S279` plus held cue in `S278` | Board frames 3500–3508 s follow the travel window 3464–3477.2 s |
| B87 | 4 visible stones | Existing visual-origin candidate | No comparable travel interval |

B26 supplies the closest temporal contact between motion and a board observation, but overlapping timestamps alone do not prove that the tracked yellow object is the same stone in the partial board. B57 has a plausible origin-to-travel sequence, yet no verified physical track connects `S278` to `S279` or identifies which later board stone resulted from that delivery. The other three board windows have no comparable travel interval in this handoff. All observations remain partial and in unitless house coordinates.

Every row explicitly marks delivered-stone-to-board identity, physical state transition and simulation readiness as **false**. The project still needs view-aware physical identity and complete settled-board coverage before it can reconstruct a game state or drive a coaching simulation. Run `python prototype/scripts/export_china_board_union_handoff.py` to verify the JSON against its hashed inputs.
