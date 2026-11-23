# Current Pipeline Architecture & 39-Module Code Map

This document is the complete inventory and reading guide for the active
left/right split-screen curling pipeline under `prototype/`. Historical research
scripts were archived in git history (through commit `1e6c5e8`); `prototype/`
now contains only the **39 active Python modules**, **5 configuration files**,
**4 web UI / labelling files**, and **35 test files**.

## End-to-End Data Flow

```text
Source 1080p MP4 + Explicit Dual-Panel Camera Calibration
  │
  ├─ Stage 1 · observations  (python -m prototype.learned_event_pipeline)
  │    ├─ Pass 1 (iGPU): YOLOv8 stone detector + ByteTrack + dual-hog scheduling
  │    │    → observations/observations.jsonl, events.json
  │    └─ Pass 2 (CPU):  1 Hz probe + scheduled SIFT similarity registration
  │         + YOLOv8-seg foreground masking + height-corrected rink projection
  │         + 20 s RapidOCR scoreboard polling
  │         → observations/match-observations.jsonl, score-observations.jsonl
  │
  ├─ Stage 2 · stone_colours (python -m prototype.track_colours)
  │    └─ Unified OpenCLIP ViT-B-32 colour classifier across all tracked stones
  │         (sequential 180-frame GOP-aware video decoding)
  │         → track-colours.json
  │
  ├─ Stage 3 · trajectories  (python -m prototype.product_pipeline --stage assemble)
  │    ├─ Calibrated dual-panel hog-crossing promotion + cross-view handoff
  │    ├─ OpenCLIP colour attachment + shared-rink projection + camera consistency
  │    ├─ Receiving-track quiet-board throw extents + state timeline
  │    └─ Synchronized top-view trajectory viewer (result/trajectories/)
  │
  ├─ Stage 4 · boards        (python -m prototype.product_pipeline --stage boards)
  │    ├─ Per-throw before/after board reconstruction, collision ID-swap repair,
  │    │    duplicate-box merging, pre-hog fallback & post-settle occlusion recovery
  │    │    → result/throws/effects.json + Throws viewer
  │    ├─ Lightweight frame-indexed board viewer (result/boards/)
  │    ├─ Sending & receiving crop-period spin probe (result/throws/revolutions.json)
  │    └─ End segmentation, board vs OCR score & rock-pair kinematics
  │         → result/score-and-rocks.json
  │
  └─ Stage 5 · report        (python -m prototype.product_pipeline --stage finish)
       └─ result/summary.json, calibration evidence viewer & result/index.html
```

---

## Guided Reading Order (All 39 Active Modules)

### 1. Workbench Server, UI & Orchestration (`4` modules + `4` UI files)
- [`prototype/workbench.py`](../prototype/workbench.py): HTTP API server (with byte-range video streaming), job lifecycle (`prepare`, `execute`, `retry`, `rebuild_outputs`), code snapshotting (`44` files), reviews, and `/events` / `/score-and-rocks` / `/stone-histories` endpoints.
- [`prototype/product_pipeline.py`](../prototype/product_pipeline.py): Stage runner (`assemble`, `boards`, `finish`) and unified `attach_event_colours()`.
- [`prototype/review_presentation.py`](../prototype/review_presentation.py): Read-only view preparation for imported runs.
- [`prototype/public_event_audit.py`](../prototype/public_event_audit.py): Strict frame-grid integrity verifier (`verify_scan`) for observation/detection reuse.
- UI & utility files: [`workbench.html`](../prototype/workbench.html), [`calibration_ui.js`](../prototype/calibration_ui.js), [`calibration_template.js`](../prototype/calibration_template.js), [`source_label_tool.html`](../prototype/source_label_tool.html).

### 2. Explicit Camera Calibration & Geometry (`9` modules)
- [`prototype/calibration_store.py`](../prototype/calibration_store.py): Immutable source-hash-bound calibration frames, previews, confirmations, and per-job bundle snapshotting.
- [`prototype/rink_template.py`](../prototype/rink_template.py): Interactive connected rink-template homography fitter (`operator_template_alignment_v1`).
- [`prototype/rink_calibration.py`](../prototype/rink_calibration.py): Landmark geometry, panel homography checks, validity intervals, and bundle loader.
- [`prototype/pinhole_calibration.py`](../prototype/pinhole_calibration.py): Pinhole physical camera refinement for point-marked calibrations.
- [`prototype/calibration_pose.py`](../prototype/calibration_pose.py): Reference-frame SIFT pose support check.
- [`prototype/calibrated_camera_geometry.py`](../prototype/calibrated_camera_geometry.py): Per-frame SIFT similarity RANSAC camera alignment with parallel left/right panels and optional half-resolution fast scale.
- [`prototype/camera_foreground.py`](../prototype/camera_foreground.py): Pinned YOLOv8-seg foreground person mask excluding players/wheelchairs from SIFT keypoints.
- [`prototype/body_localization.py`](../prototype/body_localization.py): Planar projection and height-adjusted stone centre localization (`cap_with_body_support` / `body_box_center`).
- [`prototype/stone_measurement.py`](../prototype/stone_measurement.py): Clipped-box support check (`body_point_support`) preventing cropped border boxes from corrupting geometry.
- [`prototype/calibration_review.py`](../prototype/calibration_review.py): Read-only HTML calibration evidence viewer (`result/calibration/index.html`).

### 3. Pass 1 & Pass 2 — Detection, Tracking, Observations & OCR (`7` modules)
- [`prototype/learned_event_pipeline.py`](../prototype/learned_event_pipeline.py): Two-pass observation runner (`Pass 1` iGPU detection/tracking + dual-hog scheduling; `Pass 2` 1 Hz probe + scheduled SIFT geometry + OCR).
- [`prototype/stone_detector.py`](../prototype/stone_detector.py): YOLOv8 stone detector adapter with explicit `openvino_gpu` or `pytorch` backends (no silent fallback).
- [`prototype/detection_cache.py`](../prototype/detection_cache.py): Verified SHA-256-bound detector replay / interrupted-prefix resumption.
- [`prototype/line_crossing_events.py`](../prototype/line_crossing_events.py): Segment-crossing detector used for calibrated hog lines and scheduling.
- [`prototype/match_observation.py`](../prototype/match_observation.py): Explicit-calibration per-frame board observer (`MatchObserver`), coverage/gap tracker, and scheduled inactive-interval skipper.
- [`prototype/scoreboard_observation.py`](../prototype/scoreboard_observation.py): RapidOCR scoreboard polling retaining raw tokens and abstaining when unreadable.
- [`prototype/score_grid.py`](../prototype/score_grid.py): Parses team score rows and per-end grid cells from OCR tokens.

### 4. Unified Stone Colour Classification (`2` modules)
- [`prototype/track_colours.py`](../prototype/track_colours.py): Samples crops across every tracked stone using sequential 180-frame GOP-aware decoding and classifies red vs. yellow via OpenCLIP.
- [`prototype/stone_colour_model.py`](../prototype/stone_colour_model.py): Local-cached OpenCLIP ViT-B-32 zero-shot stone colour model wrapper.

### 5. Event Aggregation, Cross-View Handoff & Shared-Rink Trajectories (`8` modules)
- [`prototype/directional_event_aggregate.py`](../prototype/directional_event_aggregate.py): Builds unified throws by promoting unclaimed calibrated receiving hog crossings (`M000xx`), pairing opposite-panel departures, filtering `<= 2`-frame unconfirmed pixel-line flickers, and retaining unmatched camera fragments.
- [`prototype/directional_handoff.py`](../prototype/directional_handoff.py): Metric hog-crossing detector (`metric_crossings`), bidirectional temporal/colour handoff hypotheses, and bounded (`<= 35 s`) short-of-hog approach recovery for hogged stones.
- [`prototype/camera_motion_role.py`](../prototype/camera_motion_role.py): Determines whether a crossing is `departure` or `receiving` from calibrated motion direction relative to the house.
- [`prototype/learned_event_aggregate.py`](../prototype/learned_event_aggregate.py): Joins event records with per-frame pixel and geometry observations.
- [`prototype/rink_coordinates.py`](../prototype/rink_coordinates.py): Panel-aware local-to-shared-rink coordinate transforms (`TEE_DISTANCE_M = 34.747 m`).
- [`prototype/cross_camera_consistency.py`](../prototype/cross_camera_consistency.py): Computes simultaneous two-camera disagreement metrics on overlapping links.
- [`prototype/scripts/enrich_rink_aggregate.py`](../prototype/scripts/enrich_rink_aggregate.py): Attaches shared-rink coordinates, gaps, and endpoint diagnostics to every segment.
- [`prototype/scripts/build_state_timeline.py`](../prototype/scripts/build_state_timeline.py): 1 Hz observed/inferred match state timeline (deliveries, house counts, OCR totals).
- [`prototype/scripts/render_rink_viewer.py`](../prototype/scripts/render_rink_viewer.py): Synchronized shared-rink top-view trajectory viewer (`result/trajectories/index.html`).

### 6. Per-Throw Boards, Physics Repair, Spin, Score & History (`7` modules)
- [`prototype/throw_effect.py`](../prototype/throw_effect.py): Core per-throw engine — deterministic `quiet_interval()` settle detection, hard-sphere collision ID-swap repair (`repair_collision_swaps`), overlapping duplicate tracker box merging, pre-hog registered `before`-window fallback, post-settle stationary occlusion recovery, house scoring, and the `Throws` viewer (`result/throws/index.html`).
- [`prototype/house_points.py`](../prototype/house_points.py): Exact curling radial distance house scoring (`points_lying`, abstaining if any in-house stone lacks colour).
- [`prototype/post_throw_state.py`](../prototype/post_throw_state.py): Lightweight frame-indexed `Stone observations` viewer (`build_board_viewer`) + OpenCV NMS duplicate box suppression (`result/boards/index.html`).
- [`prototype/board_timeline.py`](../prototype/board_timeline.py): Chunked JS frame-indexed board storage backing `Stone observations`.
- [`prototype/throw_revolutions.py`](../prototype/throw_revolutions.py): Development crop-period autocorrelation probe (sending + receiving fallback), time-based smoothing, quadrature loop sense, filmstrip renderer, and clearly labelled constant-rate whole-throw extrapolation (`physical_revolutions: null`).
- [`prototype/match_score_and_rocks.py`](../prototype/match_score_and_rocks.py): Direction-reversal end segmentation, board vs. OCR end-by-end score comparison, entry speed & lateral curl kinematics, and rule-based rock-pair summaries (`1–2` Lead through `7–8` Skip).
- [`prototype/stone_history.py`](../prototype/stone_history.py): Strict uninterrupted multi-throw stone history chains across throws with chronological swap mapping.

---

## Configuration Files (`prototype/config/`)

1. [`workbench.json`](../prototype/config/workbench.json) — active workbench profile (`.venv-detector`, OpenVINO GPU, explicit calibration required).
2. [`line-events-5hz.json`](../prototype/config/line-events-5hz.json) — 5 Hz detector/tracker configuration (`confidence=0.1`, ByteTrack).
3. [`bytetrack-5hz.yaml`](../prototype/config/bytetrack-5hz.yaml) — ByteTrack tracker thresholds tuned for 5 Hz (`track_low_thresh=0.1`).
4. [`learned-directional-two-view-explicit-calibration.json`](../prototype/config/learned-directional-two-view-explicit-calibration.json) — explicit-calibration geometry, two-pass scheduling (`probe_hz=1.0`, `before_s=12.0`, `primary_before_s=16.0`, `after_s=35.0`), SIFT registration, YOLOv8-seg foreground mask, and RapidOCR config.
5. [`stone-colour.example.json`](../prototype/config/stone-colour.example.json) — OpenCLIP ViT-B-32 colour classifier configuration.

## Scientific Boundaries
- Explicit operator calibration defines geometry; absolute metric error against independent ground truth remains unmeasured.
- Cross-view links, tracker IDs, collision-swap repairs, and rule-based rock pairs remain explicitly provisional (`physical_identity_verified: false`).
- Crop-period spin estimates are development probes (`physical_revolutions: null`, never inferred from translation alone or ODE solvers).
- Skip-broom aiming was intentionally excluded: wheelchair skips frequently do not plant a broom on the ice, and a broom marks aiming line rather than intended final resting position or shot weight.
