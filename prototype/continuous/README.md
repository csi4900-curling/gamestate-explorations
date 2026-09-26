# Continuous video experiment

Open http://127.0.0.1:8765/continuous/ with the local workbench running.

This processes the contiguous source passage 37:40–39:10 of Canada–Korea (`aWXo6XeUFQw`) at original 1920×1080 resolution. The MP4 is actual video, without audio; playback and detection overlays share its clock. Every frame is decoded. Detection and camera registration run on every half-second, for both camera panels, with no manual selection of favourable frames. Between samples the display holds the preceding observation for at most half a second.

The existing colour-cap detector is unchanged. Each sample independently registers the camera against its source-specific reference image. Rejected registration produces an unavailable observation. Association uses colour and nearest pixel distance, a 70-pixel gate, one-to-one greedy assignment, and 1.5-second expiry. IDs are provisional and camera-local. Missing detections are never emitted as observed stones. Three recent observations qualify a track as persistent; at least five observations spanning two seconds, within five pixels of the current point, qualify as visually stable. This does not detect shot boundaries or establish that all stones have stopped.

The board displays uncorrected cap projections. Above-ice parallax, merged caps, equipment false positives, occlusion, camera motion and identity switches remain unresolved. No complete board, score, delivery count, active end, or simulator-ready state is claimed. The two panels are not fused. The clip is development material, not an independent test set. Temporal persistence is not evidence of physical stone-position accuracy.

Reproduce processing from the included clip:

```sh
feasibility/scripts/python.sh prototype/scripts/process_continuous.py
feasibility/scripts/python.sh -m unittest discover -s prototype/tests
```

The processor currently expects this exact source, resolution, and start time. Generic uploads still use the earlier observation index; arbitrary-video analysis is not implemented. `timeline.json` contains all sampled results and runtime, `processing.log` records execution, and `browser-check.json` records playback checks.
