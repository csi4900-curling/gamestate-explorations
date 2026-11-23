# App-workbench guide

The app-workbench is the public entry point for new analyses. This guide describes
the active application path in `prototype/workbench.py` and
`prototype/product_pipeline.py` (39 active modules, single `.venv-detector`
runtime). It describes implementation, not independently validated trajectory
performance.

## Start and configure

From the project root:

```sh
./curling-workbench
```

Open **http://127.0.0.1:8766**. The launcher uses
`feasibility/scripts/python.sh` to run `prototype.workbench`.

The default [profile](../prototype/config/workbench.json) specifies the Python
environment (`.venv-detector/bin/python`), OpenCLIP colour dependencies and
cache, YOLOv8 stone detector weights/export, runtime environment, and pipeline
configuration files. Its default backend is explicit Intel GPU inference
(`openvino_gpu`) with pinned local OpenCL libraries. CPU execution requires an
explicit `pytorch` profile; there is no silent device fallback.

To use an alternative configured profile or isolated job store:

```sh
./curling-workbench --profile /absolute/path/to/profile.json --data /absolute/path/to/job-store --port 8767
```

Only one server may own a job store. The default store is `workbench-data/`.
For supervised Linux operation with this checkout at `~/curling-project`:

```sh
systemctl --user link "$PWD/deploy/curling-workbench.service"
systemctl --user start curling-workbench.service
systemctl --user status curling-workbench.service
journalctl --user -u curling-workbench.service
```

Stop that service before starting another server against the same store:

```sh
systemctl --user stop curling-workbench.service
```

## Analyse and review

Load a local recording (or upload it), select an interval, and open **Camera
calibration**. Choose clear source frames for both panels, align the interactive
rink template (or use the advanced point editor), inspect the projected overlays
for both cameras, and confirm the operator record. Explicit calibration defines
both hog lines automatically — no manual event line is required.

The calibration workflow fits a physical camera from operator markings and
reuses it across frames through SIFT similarity RANSAC. A pinned upstream
YOLOv8-seg person segmenter excludes predicted foreground from registration
feature selection; it does not identify stones or calibrate the rink.
Unsupported framing changes and insufficient alignment support leave explicit
geometry gaps. Saved source frames, inputs, reviewer, and checks are snapshotted
with every run. Engineering residual checks do not certify absolute position
accuracy.

Completed runs open on **Throws**: before-board observations, observed paths of
moving stones, collision ID-swap repairs, recovered post-settle occlusions,
settled board, points lying, kinematics, and crop-period spin estimates.
**Stone observations**, **Top-view trajectory**, **Stone history**, and **Match
score & rock-pair comparison** provide synchronized review. Candidate reviews
persist separately from predictions and can be downloaded as JSON.

## Application execution path

`Workbench.prepare()` saves source identity, interval, operator settings,
calibration bundle, and job specification, and snapshots the active `prototype/`
files (44 files) with SHA-256 hashes into `job/code/`. `Workbench.execute()`
runs five stages in order:

| Stage | Invoked implementation | Purpose |
| --- | --- | --- |
| `observations` | `python -m prototype.learned_event_pipeline` | Pass 1: OpenVINO GPU YOLOv8 stone detection + ByteTrack + dual-hog scheduling. Pass 2: 1 Hz probe + scheduled SIFT camera registration + RapidOCR scoreboard polling. |
| `stone_colours` | `python -m prototype.track_colours` | Unified OpenCLIP ViT-B-32 colour classification across all tracked stones (sequential GOP-aware video decoding). |
| `trajectories` | `python -m prototype.product_pipeline --stage assemble` | Calibrated dual-panel hog-crossing aggregation & promotion (`directional_event_aggregate.py`), colour attachment, shared-rink projection, camera consistency, throw extents, state timeline, and synchronized trajectory viewer. |
| `boards` | `python -m prototype.product_pipeline --stage boards` | Per-throw before/after boards, hard-sphere collision ID-swap repair, duplicate box merging, post-settle occlusion recovery (`throw_effect.py`), lightweight frame-indexed board viewer (`post_throw_state.py`), crop-period spin probe (`throw_revolutions.py`), and end/score/rock-pair analytics (`match_score_and_rocks.py`). |
| `report` | `python -m prototype.product_pipeline --stage finish` | Result summary, explicit calibration review page, media URL wiring, and linked result landing page. |

Actual per-run commands and wall times are recorded in `stages.json`.

## Saved outputs and recovery

Each local `workbench-data/jobs/<job-id>/` includes `spec.json`, `job.json`,
`code/`, per-run configuration files, `stages.json`, stage logs, observations,
`track-colours.json`, and `result/`.

- **Detector-scan selection in a new analysis:** reuses a verified complete scan
  for the exact interval, or an interrupted scan's committed prefix on the same
  starting frame and sampling grid. Remaining detections are computed afresh;
  tracking, geometry, and downstream stages rerun.
- **Retry remaining stages:** after a failed/interrupted run with a complete
  observation scan, verifies saved coverage and copies observations into a new
  run while preserving the failed run intact.
- **Rebuild outputs:** reuses verified completed observations (and verified
  `track-colours.json` when inputs match) in a separate development run with
  current downstream code. Original outputs remain untouched.

## Verification

Run the complete test suite (zero extra dependency paths required):

```sh
PYTHONPATH="$PWD" feasibility/scripts/python.sh -m pytest -q prototype/tests
```

See [CURRENT_PIPELINE.md](CURRENT_PIPELINE.md) for the complete 39-module code
map.
