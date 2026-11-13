# Continuous video experiment

Open http://127.0.0.1:8765/continuous/ with the local workbench running.

This processes the contiguous source passage 37:40–39:10 of Canada–Korea (`aWXo6XeUFQw`) at original 1920×1080 resolution. The MP4 is actual video, without audio; playback and detection overlays share its clock. Every frame is decoded. Detection and camera registration run on every half-second, for both camera panels, with no manual selection of favourable frames. Between samples the display holds the preceding observation for at most half a second.

The existing colour-cap detector is unchanged. Each sample independently registers the camera against its source-specific reference image. Rejected registration produces an unavailable observation. Association uses colour and nearest pixel distance, a 70-pixel gate, one-to-one greedy assignment, and 1.5-second expiry. IDs are provisional and camera-local. Missing detections are never emitted as observed stones. Three recent observations qualify a track as persistent; at least five observations spanning two seconds, within five pixels of the current point, qualify as visually stable. This does not detect shot boundaries or establish that all stones have stopped.

The board covers only the configured world bounds around each house. On the left camera these are x = −2.375 to 2.375 m and y = −6.401 to 1.975 m; a delivered stone higher up the rink is rejected before it appears as a board dot, even when camera registration succeeds. For T11 at clip time 43.5 s, the observed yellow cap near pixel (466, 215) projects to about y = −9.2 m under the viewer's homography and is outside that bound. The source-view throw tracker uses a separate early-ice region and may still detect its passage. A red tentative cap marker near a player can also be a false positive. The [far-geometry audit](FAR-GEOMETRY.md) checks the independent hog-line marking and clarifies that the cutoff is a scope choice rather than a proven accuracy limit.

The automatic board dots display uncorrected cap projections. The optional T11 overlay on the left board is a separate 31-point departure trace from `../cross-view/T11-departure.json`, time-aligned to clip 43.5–46.7 s and mapped using its conditional 0.136 m cap-height correction. Its dashed hog-line boundary at y = −6.401 m marks the end of the original accepted world bounds, not a measured accuracy failure. The shaded area and trail are explicitly provisional: no independent ground points there establish metric accuracy. The trace is excluded from `timeline.json` and the automatic detection count. Above-ice parallax, merged caps, equipment false positives, occlusion, camera motion and identity switches remain unresolved. No complete board, score, delivery count, active end, or simulator-ready state is claimed. The two panels are not fused. The clip is development material, not an independent test set. Temporal persistence is not evidence of physical stone-position accuracy.

Reproduce processing from the included clip:

```sh
feasibility/scripts/python.sh prototype/scripts/process_continuous.py
feasibility/scripts/python.sh -m unittest discover -s prototype/tests
```

The processor currently expects this exact source, resolution, and start time. Generic uploads still use the earlier observation index; arbitrary-video analysis is not implemented. `timeline.json` contains all sampled results and runtime, `processing.log` records execution, and `browser-check.json` records playback checks.

**T11 receiving-view correction:** The 5.8 s blank in the earlier joined trajectory is primarily a filter artifact. The right camera's standard world bound ends at y = 6.401 m. In a targeted rerun with the same detector and a provisional y ≤ 22 m bound, T11-like moving yellow cap proposals appear on the right from clip time 46.7 s, simultaneous with the final left-camera proposal, through the original right-camera start at 52.5 s. Those extra positions have not been integrated into this viewer or independently validated as metric coordinates; see [the cross-view audit note](../cross-view/README.md).
