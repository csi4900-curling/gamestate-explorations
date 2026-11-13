# Canada–Slovakia 2024: partial boards after provisional events

The fixed [event screen](CANADA-SLOVAKIA-2024-DROPOUT-TRANSFER-RESULTS.md) retains 17 provisional passages in the 1650–2760 s interval. A separate [post-event observation audit](canada-slovakia-2024-post-event-partial-boards-v2-development.json) now samples the receiving camera **after each selected motion path**, stopping before the next passage candidate or 35 s after the crossing. It emits **14 partial view-local board observations containing 41 stable stone observations**. Three events have no eligible quiet tail, so their post-event board is explicitly unknown. No complete game state or simulator input is produced.

| Evidence | Count |
| --- | ---: |
| Screened provisional events | 17 |
| Eligible quiet tails | 14 |
| Tails with at least one stable visible stone | 14 |
| Stable stone observations across those tails | 41 |
| Events without enough quiet time before another candidate | 3 (S16, S19, S24) |
| Sampled frames / accepted registrations | 328 / 320 |

The three missing tails are **not registration failures**. S16's next candidate begins before its receiving path ends; S19 and S24 similarly lack the required four seconds before the next candidate. The first output incorrectly grouped them under `no_registered_tail_frames`; the preserved [v1 artifact](canada-slovakia-2024-post-event-partial-boards-development.json) differs from v2 only in those three status strings. It is safer to leave a board unknown than to step past a possible next delivery.

For each eligible tail, the audit keeps same-colour proposals in the near-house region (|x|≤2.375 m and |y|≤4.5 m in that camera's local ice plane). A stone observation needs at least three registered frames spanning four seconds, ≤0.18 m position spread, and a sighting within two seconds of the last registered frame. Its exported position is the median of provisional ground-centre projections. The output retains per-frame proposals, registration status, source times, camera view, and input/code hashes. No official board positions or throw labels enter inference.

The [source frame at 2153 s](canada-slovakia-board-source-2153.jpg) visibly shows the three near-house stones reported after S13. The [source frame at 2752 s](canada-slovakia-board-source-2752.jpg) shows several stones after S27; the audit retains six stable near-house observations and does not claim that all visible stones in the image were counted. These are qualitative checks on two selected frames, not a board-accuracy estimate.

The coordinates are **camera-local and conditional**: calibration, camera intrinsics, stone height, and cap/body localization have not been validated against measured rink coordinates. The two views are not joined into a single physical frame. A stable visual proposal can still be an impostor, and a nearby player or stick can occlude a real stone. The delivered stone might still be moving when this window begins or could settle outside the observed region. Stone identity across events, exact settle time, full-sheet completeness, score, spin, and collision history remain unknown. Every row records `simulation_ready: false`.

This is a concrete video-to-partial-state handoff. The next validation step is to compare **source-only** post-shot boards against an independent board reference on a recording with reliable shot timing, while preserving missing tails and view limitations. Physics replay requires continuous, calibrated trajectories and persistent stone identities in addition to a settled board.

An [adjacent partial-board comparison ledger](CANADA-SLOVAKIA-2024-ADJACENT-PARTIAL-BOARDS.md) now examines consecutive accepted events when both boards exist in the same camera and no other passage candidate intervenes. It finds 16 conservative spatial associations across 8 comparable pairs. These are repeated local observations, not verified stone identities or full state transitions.
