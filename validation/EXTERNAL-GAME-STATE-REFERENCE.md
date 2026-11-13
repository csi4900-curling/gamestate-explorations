# External shot-state reference: CSAS 2026 mixed doubles

The [CSAS 2026 data challenge](https://statds.org/events/csas2026/challenge.html) publishes shot-by-shot curling states in a [public CSV repository](https://github.com/CSAS-Data-Challenge/2026). Its `Stones.csv` has match/end/shot identifiers, throwing team and player, shot task, handle direction, and the positions of each stone **after** the shot. The challenge page describes over 26,000 shot observations from international mixed-doubles competitions.

This is a useful *schema and downstream-analysis reference*, not a throw-event benchmark for our broadcasts. The documented rows do not provide video timestamps, moving-stone tracks, angular speed, or revolution counts. They also cover mixed doubles, whereas our current full-match validation source is wheelchair curling. We must not count a match in this dataset as validation unless the exact corresponding footage and synchronization are established.

For our own video-derived game state, preserve these distinctions explicitly:

| Quantity | Meaning | Evidence required |
| --- | --- | --- |
| `event_start_s`, `event_end_s` | Broadcast-video interval | Independently checked throw-event boundaries |
| `stone_id`, `team_id`, `end_id`, `shot_id` | Game identity and order | Video/scoreboard evidence or a matched results feed |
| `x_m`, `y_m`, `in_play` | Settled stone state after a throw | Registered stone detections, with occlusion and out-of-view status kept distinct |
| `rotation_direction` | Clockwise/counterclockwise turn | Visible handle/marker motion or independently verified shot metadata |
| `revolutions`, `angular_speed_rad_s` | Measured stone rotation | Unwrapped visual orientation over time; the center trajectory alone is insufficient |
| `evidence` and `uncertainty` | Provenance and confidence for each value | Source camera, timestamps, calibration, observation coverage, and review status |

The CSV's `Handle` field records direction only (0 clockwise, 1 counterclockwise); it cannot supply a revolution count. Its coordinates use dataset-specific units and sentinel values (0 for not yet thrown, 4095 for out of play), so any comparison requires an explicit coordinate and status conversion. Missing, occluded, and out-of-play stones must remain distinguishable in our representation.

Potential use: test game-state serialization, stone-order logic, and downstream coaching/simulation queries against a large public set of **settled** boards. It cannot measure segmentation recall or precision on our videos and cannot replace independent review of our reserved match.
