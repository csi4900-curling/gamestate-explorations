# Provisional event-to-board evidence handoff

The [machine-readable handoff](pwg2022-provisional-event-board-evidence.json) joins existing video-derived partial board observations to provisional video event candidates in three Beijing 2022 recordings. It matches only when the source-video SHA-256 and the exact delayed broadcast-counter update time agree; it never joins by shot order, nearest time, or official diagram position. Duplicate or missing matches remain explicit statuses in the join code.

All **seven** exported partial boards have exactly one source-scoped candidate with the same counter update. The resulting links carry **22 video stone observations**. Each board observation occurs after its shared counter update, but the counter itself may update after the physical delivery. A shared timestamp is therefore a bookkeeping link, **not proof** that the candidate is the delivered stone or that any observed board stone is its settled position.

The export retains source hashes, event candidate IDs, broad release windows, candidate colour status, board observation intervals, house-radius coordinates, and local stone observations. Every link states `delivered_stone_identity: null`, `physical_settle_time_s: null`, `board_completeness: unknown_from_video`, and `simulation_ready: false`. No official diagram positions are copied into the video board observations.

This is the first concrete event-to-state data handoff, but it is sparse: the seven snapshots are selected from different ends, with no validated adjacent before/after boards. It cannot yet reconstruct state transitions, continuous trajectories, or 2D/3D physics. The next required evidence is complete video board coverage around a throw, persistent stone identity across the camera cut, metric calibration, and independent event validation. The reserved independent source was not used.

A later [targeted adjacent-board extension](ADJACENT-BOARD-TRANSITIONS.md) adds two Swiss end-two snapshots and two local observed transitions, producing an extended nine-board handoff. The original seven-board export remains frozen as the first result.
