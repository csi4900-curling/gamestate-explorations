# App-workbench guide

The app-workbench is the public entry point for new analyses. This guide describes
the current application path, checked against `prototype/workbench.py` and
`prototype/product_pipeline.py` on 12 November 2026. It describes implementation,
not independently validated trajectory performance.

## Start and configure

From the project root:

```sh
./curling-workbench
```

Open **http://127.0.0.1:8766**. The launcher uses
`feasibility/scripts/python.sh` to run `prototype.workbench`.

The default [profile](../prototype/config/workbench.json) specifies separate
inference and state Python environments, detector weights/export, colour and
state dependency directories, model cache, runtime environment and pipeline
configuration files. Its default backend is explicit Intel GPU inference with
local pinned OpenCL libraries. CPU execution requires an explicit `pytorch`
profile. There is no silent device fallback.

A fresh clone does not include all runtime assets. Before analysing a recording,
provision the environments and model assets named by the selected profile and its
referenced configurations. Several default paths are specific to the development
machine; configure those paths for the host. The model/colour/OCR dependencies,
recordings and full local evidence are not all distributed with the code.

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

Load a local recording or upload it, select an interval, and open **Camera
calibration**. Choose clear source frames for each panel, mark visible ring arcs,
lines or named intersections, reserve separate check points, inspect the projected
markings and confirm the operator record. Select saved records whose pose validity
intervals cover the analysis interval without ambiguous overlaps. Set the event
crossing line, team/colour mapping and physical settings in the analysis form.

The default calibration workflow fits a physical camera from operator markings
and reuses it through source-image similarity alignment. A pinned upstream person
segmenter excludes predicted foreground from registration feature selection;
it does not identify stones or calibrate the rink. Unsupported framing changes
and insufficient alignment support leave explicit geometry gaps. Calibration
without longitudinal perspective support is limited to its bounded marked region.
The saved source frames, inputs, reviewer and checks remain part of the run.
Engineering residual checks do not certify absolute position accuracy.

Completed runs open on **Throws**: before-board observations, paths of moving
stones, the proposed quiet board and points lying on it. **Trajectories** and
**Stone observations** provide synchronized source review. Unresolved tracks,
missing geometry and ambiguous camera associations require review. Candidate
reviews persist separately from predictions and can be downloaded as JSON.
Review-subset precision is not full-match accuracy; missed-event labels are
needed to measure recall.

## Application execution path

`Workbench.prepare()` saves the source identity, interval, operator settings,
calibration bundle and job specification. It copies executable/view assets from
`prototype/` into the job's `code/` directory and records hashes. Shared model and
research assets remain external inputs; this snapshot is not a portable runtime.
`Workbench.execute()` runs the following stages in order:

| Stage | Invoked implementation | Purpose |
| --- | --- | --- |
| `observations` | `scripts/run_throw_pipeline.py` with `--event-line-config`, `--events-only` and `--match-state-config`; dispatches to `learned_event_pipeline.py` | Learned detections, tracking, event candidates and synchronized geometry/board observations. |
| `colour` | `scripts/classify_event_colours.py` | Existing OpenCLIP component classifies event stone colours. |
| `trajectories` | `product_pipeline.py --stage assemble` | Directional aggregation, camera-consistency annotations, throw extents, state timeline and trajectory/fragment viewers. |
| `stone_colours` | `track_colours.py` | Existing colour component classifies tracked stones. |
| `boards` | `product_pipeline.py --stage boards` | Motion/state proposals and the per-throw board-change view using `throw_effect.py`. |
| `report` | `product_pipeline.py --stage finish` | Result summary, calibration evidence view and linked result page. |

The observation runner also contains historical routes. Its filename alone does
not identify the app's behavior: the saved command and configuration select the
learned-event route above. The actual per-run commands and times are recorded in
`stages.json`.

Useful code entry points:

- [Application server and orchestration](../prototype/workbench.py)
- [Application UI](../prototype/workbench.html)
- [Calibration records](../prototype/calibration_store.py)
- [Learned observation pipeline](../prototype/learned_event_pipeline.py)
- [Product assembly](../prototype/product_pipeline.py)
- [Verified detector reuse](../prototype/detection_cache.py)
- [Review presentation](../prototype/review_presentation.py)
- [Metric/identity evaluator](../prototype/trajectory_benchmark.py)

## Saved outputs and recovery

Each local `workbench-data/jobs/<job-id>/` includes `spec.json`, `job.json`,
`code/`, per-run configuration files, `stages.json`, stage logs, observations and
results. Explicit-calibration runs also snapshot calibration records and assets.
The result directory contains `summary.json`, trajectory aggregates, a state
timeline and the Throws, Trajectories, Stone observations and calibration viewers.
The aggregates retain samples separately from the throw-extent display copy.

A process restart preserves outputs and marks queued/running jobs interrupted.
The service restarts the server after process failure; it does not automatically
restart expensive analysis work.

- **Detector-scan selection in a new analysis:** reuses a verified complete scan
  for the exact interval, or an interrupted scan's committed prefix on the same
  starting frame and sampling grid. Remaining detections are computed afresh;
  tracking, geometry and later stages rerun.
- **Retry remaining stages:** after a failed/interrupted run with a complete
  observation scan, verifies saved coverage and copies observations into a new
  run. The failed run remains intact.
- **Rebuild outputs:** uses verified completed observations in a separate
  development run with current downstream code. Original predictions and outputs
  remain preserved. This does not measure fresh inference runtime or transfer.

Reuse provenance is recorded with the new run. A partial scan is not labelled
complete. A job reaching `done` means execution finished, not that its accuracy
or physical identity passed acceptance.

## Verification

Focused workbench checks:

```sh
PYTHONPATH=/path/to/state-deps:$PWD feasibility/scripts/python.sh -m pytest -q \
  prototype/tests/test_workbench.py \
  prototype/tests/test_workbench_detection_reuse.py \
  prototype/tests/test_trajectory_benchmark.py \
  prototype/tests/test_throw_effect.py
```

Broader component/behavioral suite:

```sh
PYTHONPATH=/path/to/state-deps:$PWD feasibility/scripts/python.sh -m pytest -q prototype/tests \
  --ignore prototype/tests/test_online_checkpoint.py
```

Replace the dependency path for the host. The excluded checkpoint test requires
PyTorch, which the default state environment does not provide. Neither command
establishes complete-pipeline accuracy. Acceptance requires the actual app run
and synchronized outputs, timestamped independent references, event TP/FP/FN,
physical identity, observable coverage/gaps and metric error. See the
[acceptance contract](LEFT_RIGHT_REQUIREMENTS.md).

## Known limits

Physical identity, absolute geometry accuracy, complete-match reliability and
physical revolution counts remain unvalidated. Provisional position targets are
10 cm median and 25 cm p95; camera disagreement cannot substitute for independent
metric references. All inspected CAN/NOR runs remain development evidence.
Norway–Sweden remains reserved for frozen evaluation.

Scoring/state code includes OCR chronology, event-count end hypotheses and
estimated house points. Missed/extra events can misalign inferred ends; tracker
fragmentation affects associated board state. Per-throw points are not official
match totals. Historical score/OCR/spin descriptions and their caveats are retained
in the [previous README](history/README-before-workbench-navigation-2026-11-12.md);
they are not a promise that every panel appears in the current focused UI.
