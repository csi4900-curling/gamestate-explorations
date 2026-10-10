# Estonia S02: source-visible two-camera bridge

The two panels of the 1080p Estonia source are simultaneous camera views. There is **no camera cut at 1759 s**. The yellow stone moving downward in the right panel at 1753–1758 s appears near the top of the left panel while a yellow stone is still visible at the bottom of the right panel. The [paired source crops](yellow-s02-simultaneous-edge-overlap.jpg) show the overlap. This corrects the earlier description of a cut; the [first frozen transfer](YELLOW-CONTOUR-FIRST-TRANSFER-RESULTS.md) still failed for its documented direction and region-of-interest reasons.

A frame-level [edge visibility audit](yellow-s02-edge-timing-postreview.json) on the unchanged source counts yellow pixels in two selected edge regions. With a 50-pixel threshold at 30 Hz, right-edge visibility ends at 1758.90 s and left-edge visibility starts at 1758.17 s: **23 frames satisfy both conditions**, a roughly 0.73 s overlap. Those regions and the threshold were selected after looking at the video. The counts establish simultaneous visible yellow material in the two panels, not an independently verified physical identity.

The [left-entry contour track](yellow-s02-left-entry-to-prior-path-postreview.json) starts in a selected source-visible region at 1758.5 s and follows the yellow cap every 0.5 s through 1771.5 s. It is built without using the previous S02 path for association. The [marked source sheet](yellow-s02-left-entry-bridge-source-review.jpg) shows a continuous visible stone on seven of those frames. Only after building the track was it compared with the earlier provisional [S02 left path](left-bound-full-interval/s02-paired.json): the 11 overlapping sample centres at 1766.5–1771.5 s differ by **1.981 px on average**, 4.312 px at most, in the 1080p image. This strongly supports the left-entry-to-S02 observation link. The first-entry region and tracking parameters are post-review choices, so the agreement is diagnostic rather than an out-of-sample score.

The resulting evidence chain is: sustained right-panel image motion begins in the **1753–1754 s observation bracket**; the stone approaches the lower right-panel boundary; both panels show yellow stone-like objects during the edge overlap; a left-panel cap track begins at the upper boundary and reaches the previously preserved S02 left path. This is a **plausible cross-view physical-stone handoff**, stronger than timing alone, but not a blind identity label. The prior 1731–1752 s stationary prefix remains unverified and is excluded from the motion onset. S02's 1759.52 s line crossing is an event observation, not a release time.

This bridge does not measure physical stop, rink-coordinate trajectory accuracy, revolutions, settled board state, or full-match event precision/recall. It should enter the event/game-state handoff as provisional linked observations with source provenance and an explicit `physical_stone_identity_verified: false` field. A simulation may visualize such a hypothesis, but it must not present it as a measured full throw.

The reproducible [observation handoff](yellow-s02-cross-view-observation-handoff-postreview-v2.json) now carries five right-view body samples **plus the recovered 1758 s contour**, 27 left-view cap samples, the 23-frame edge overlap, the S02 crossing observation and hashes of every input. The [expanded-right contour transfer](../layout-router/full-2024-coverage/YELLOW-FULL-RIGHT-CONTOUR-TRANSFER.md) leaves the earlier Korea and Slovakia candidate-stop brackets unchanged. The handoff's `game_state_after` leaves release, settle, complete board, metric path, persistent identity and spin unknown; `simulation_ready` is false. It is an evidence row for later state reconstruction, not a new verified throw row.

The [full-match S38 enrichment](S38-HIGHRES-STATE-ENRICHMENT.md) links this excerpt to its provisional 360p candidate and shows why post-event board evidence must be sampled in the receiving left panel. Two yellow image caps repeat there after the passage; no complete physical board or delivered-stone identity is inferred.

Reproduce the post-review audits and sheets with:

```sh
feasibility/scripts/python.sh prototype/scripts/audit_estonia_s02_edge_timing.py
feasibility/scripts/python.sh prototype/scripts/audit_estonia_s02_left_bridge.py
feasibility/scripts/python.sh prototype/scripts/render_estonia_s02_edge_overlap.py
feasibility/scripts/python.sh prototype/scripts/render_estonia_s02_left_bridge.py
feasibility/scripts/python.sh prototype/scripts/transfer_bidirectional_full_right_contours.py
feasibility/scripts/python.sh prototype/scripts/export_estonia_s02_cross_view_bridge.py
```
