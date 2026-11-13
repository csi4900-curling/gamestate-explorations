# China partial-board/event coverage audit

The [source-scoped audit](china-board-event-coverage-v1.json) joins eight previously selected Canada–China 2022 board windows to two existing event outputs through the **same delayed counter update**. Five windows contain a stable partial board, totaling 12 stone observations. The earlier full candidate ledger has a unique counter-linked candidate in every window. The newer 112-candidate cap-fusion grounding envelope covers six of the eight windows, including three of the five windows with a partial board.

| Board window | Stable observed stones | Earlier event | Grounded cap-fusion event |
| --- | ---: | --- | --- |
| End 2, shot 11 | 1 | T026 / B25, counter-linked red | S116; red comes from the counter after ambiguous visual motion |
| End 2, shot 12 | 1 | T027 / B26, colour conflict | **Absent** |
| End 2, shot 15 | 1 | T030 / B29, red | S137; visual and counter agree |
| End 4, shot 13 | 5 | T060 / B57, red | **Absent** |
| End 6, shot 12 | 4 | T093 / B87, red | S408; visual and counter agree |

The end-two shot-12 board observation is especially easy to misread. Its visible yellow stone appears after the B26 counter update, but the legacy event candidate has unresolved colour conflict, and B26 is absent from the newer cap-fusion envelope. That partial board cannot validate T027 as the delivered yellow stone or establish that the visible stone was newly thrown. The five-stone end-four board likewise survives as a video observation even though the cap-fusion subset lacks B57. Absence from that subset is **not evidence that a physical throw did not occur**.

A later [held-origin development proposal](HELD-ORIGIN-COUNTER-RESCUE.md) supplies a separate provisional `S278/B57` event cue over ice, but it does not prove that the held stone caused the five-stone board observation. The [receiving-view travel audit](CAP-FUSION-TRAVEL-RESCUE.md) supplies provisional yellow motion in `S124` for B26; its release side and connection to the later one-stone board remain unverified.

The audit also retains the three scanned end-two windows with no stable board, so the denominator is visible. Every join is bookkeeping based on a delayed scoreboard timestamp, not a verified stone identity. All boards remain partial and all `physical_transition_verified` and `simulation_ready` fields are false. The [source-only adjacent comparison](CHINA-ADJACENT-BOARD-FIRST-TRANSFER.md) still reports two partial boards from five selected shots and no complete state.

Run `python prototype/scripts/audit_china_board_event_coverage.py` from the repository root to verify the JSON exactly against its hashed inputs and code. The runner refuses source mismatches, ambiguous legacy counter joins, altered colours in the newer event envelope, and use of the reserved independent recording.
