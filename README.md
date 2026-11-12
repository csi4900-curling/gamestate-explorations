# Curling trajectory reconstruction

Build **one reliable pipeline for left/right split-screen curling broadcasts**,
with accurate trajectories and consistent stone identity across observations,
camera views, occlusions and trajectory fragments. New recordings use the same versioned pipeline without per-video code or rule
tuning. As explicitly authorized on 9 November 2026, camera calibration is an
exposed operator step until an independently reliable learned replacement exists. Other broadcast formats and broad
transfer-learning evaluation are deferred.

**This goal is not yet achieved.** The current public runner is a development
integration with incomplete tracking and provisional identity. The discarded
receiving passes were removed in a labelled development change, with exact
final-output equivalence on a 45-second clip; full-match regression is pending.

## Local workbench — 3 November 2026

```sh
./curling-workbench
```

Open **http://127.0.0.1:8766**. The workbench loads local videos or uploads,
requires a checked source calibration, saves the event line, teams and physical dimensions, runs the shared learned
pipeline, and opens synchronized board/trajectory viewers. Jobs have immutable
code and view-asset snapshots, stage logs/timings and explicit failed/interrupted states.
Candidate reviews persist separately from predictions and can be downloaded as
JSON. Review-subset precision is not full-match accuracy; recall remains unknown
without labels for missed throws. Rotation remains experimental, with no validated
physical count.

### Throws view — 12 November 2026 (development)

Each completed run now opens on a **Throws** tab. For every detected throw it
shows the receiving-house stones before the delivered stone arrives, the
observed paths of the stones that moved, the board in the first interval where
no in-play stone moves, and the points lying on that board. It is built by
`prototype/throw_effect.py` from saved observations; detection, tracking and
geometry are unchanged. `prototype/track_colours.py` adds a colour to every
tracked stone with the existing OpenCLIP component.

This is a development replay, checked on one 14-minute NOR–CZE interval: 8 of
10 detected throws received a board and 2 stayed unresolved. Three throws were
compared with source frames by the developing agent with predictions visible;
that is not independent ground truth. Positions inherit unverified calibration,
tracker IDs are not physical identity, missed throws are not counted, and
per-throw points are not accumulated into end or match scores. Evidence is in
`validation/throw-effect-development-2026-11-11/`.

### Tests

```sh
PYTHONPATH=/path/to/state-deps:$PWD feasibility/scripts/python.sh -m pytest -q prototype/tests \
  --ignore prototype/tests/test_online_checkpoint.py
```

`test_online_checkpoint.py` needs PyTorch and runs in the detector environment.
Model weights, source recordings and most run evidence are not in the
repository; the workbench cannot analyse a new video without the detector
checkpoint named in `prototype/config/workbench.json`.

For supervised local operation on Linux, a user service is provided. With this
checkout at `~/curling-project`, run:

```sh
systemctl --user link "$PWD/deploy/curling-workbench.service"
systemctl --user start curling-workbench.service
systemctl --user status curling-workbench.service
journalctl --user -u curling-workbench.service
```

The service restarts on process failure. Interrupted analysis outputs remain
preserved. In a new analysis, the detector-scan selector can reuse an interrupted
scan's verified committed prefix and detect the remaining frames afresh;
tracking, geometry and later stages rerun. Complete scans require exact source
intervals, while prefixes require the same starting frame and sampling grid.
Neither path relabels the interrupted run as successful. Stop the service with
`systemctl --user stop curling-workbench.service` before launching another server
against the same data directory.

The current-board viewer also maintains cumulative match totals from saved
scoreboard OCR through the shared `score_sequence` module. It displays supporting
observation times, unknown values and clickable score changes; the downloaded
review report includes the score history and conflicts. This is offline
chronological inference using the whole recording, not a verified live score
reader. Score-change times are first supporting OCR samples, not independently
labelled end boundaries. Provisional house points remain separate.

Detected-throw subset scoring now has an event-keyed stone ledger, per-panel
estimated points and clickable post-throw history. It excludes unmatched stones
from that calculation, updates linked stones from current observations and holds
timestamped last positions during gaps. Holds are explicitly estimated; missing
geometry and conflicting assignments remain unresolved. This reuses existing
receiving associations and does not repair identity fragmentation. End grouping
retains its existing inferred provenance; per-throw points are never summed into
official match totals.

The reconstructed match estimate now awards one estimated result per completed
inferred end. The end remains active through its final throw and changes at the
next end's first crossing. End grouping still assumes the declared number of
detected deliveries per end (the existing default is 16); misses/extras can
misalign physical ends. Missing final-throw results produce unresolved ends and
an explicitly incomplete estimated subtotal, not a zero award. Empty association
sets display “No associated board state.” OCR remains a separate comparison.

For a new recording, open **Camera calibration** in the analysis form. Choose clear
source frames for each panel, mark visible ring arcs/lines or named intersections,
reserve separate check points, inspect the projected markings, then confirm the
operator record. Select that saved record for later runs; no code or homography
file editing is needed. Pose intervals must cover the analysis interval without
ambiguous overlaps. A fixed mapping is reused while its static image marks remain
supported. The default fits one physical camera during explicit setup, then
transports it through source-image similarity alignment. A pinned upstream person
segmenter excludes predicted foreground from image-feature selection; it does
not identify stones or calibrate the rink. Unsupported camera changes/occlusion leave explicit gaps and an
incomplete-trajectory warning. The result includes a read-only calibration viewer,
source frames, operator provenance and hashes. Residual checks are engineering
consistency checks, not independent absolute-accuracy measurements.

The trajectory state timeline leaves the absolute game end unknown without a
recent past readable scoreboard marker. It retains event-count grouping as a
separate relative hypothesis. Future scoreboard observations and later camera
role evidence are not backfilled into earlier source times.

The previous automatic experiment is preserved in
`prototype/config/workbench-legacy-baseline.json`; select it explicitly for
baseline reproduction. It is not the default product calibration path.

The default profile is [workbench.json](prototype/config/workbench.json).
It uses explicit Intel GPU inference, existing detector/colour/OCR models and separate
inference/state Python environments. Dependency/cache paths and runtime environment are configurable. The OpenCL runtime
is pinned under `workbench-data/`; select `pytorch` explicitly for CPU execution.
There is no silent device fallback.
Geometry and physical identity remain development capabilities, not independently
validated measurements. Norway–Sweden remains reserved for frozen evaluation.

To import an existing full-match development result without rerunning inference:

```sh
./curling-workbench \
  --import-result validation/post-throw-state-development-2026-10-26/public-state-attempt-0005 \
  --video validation/full-match-development-2026-10-23/source-1080p.mp4 \
  --trajectory validation/full-match-development-2026-10-23/final/viewer/index.html
```

Run data and reviews are stored in `workbench-data/`. A restart preserves outputs
and marks unfinished jobs interrupted; it does not silently restart expensive work.
For a failure after a complete observation scan, **Retry remaining stages** verifies
the saved frame coverage and copies those predictions into a new run. The failed
run stays intact, and the reuse is recorded in the downloadable report. Partial
observation scans are not presented as complete or reused by this retry action.
The older upload server indexes coarse video activity and is not this workbench.
The archived README preserves the earlier launch/status descriptions.

## Start here

- [Historical component deliverable: dense tracking, synchronized projection and spin results](validation/spin-development-2026-10-22/index.html)
- [What this deliverable implements and how to run it (French)](docs/SPIN_DELIVERABLE.md)
- [Historical pipeline audit (22 October; predates the learned-event workbench)](docs/CURRENT_PIPELINE.md)
- [Standing scope and evidence requirements](AGENTS.md)
- [Required product outputs and acceptance contract](docs/LEFT_RIGHT_REQUIREMENTS.md)
- [Established-model shortlist and spin methodology](docs/MODEL_SELECTION.md)
- [Original integrated output viewer](validation/meeting-2026-10-22/runtime/index.html)
- [Diagnostic viewer bypassing the departure ring gate](validation/meeting-2026-10-22/runtime-no-ring/index.html)
- [French supervisor report](supervisor-progress-2026-10-22.pdf)
- [Archived original-workflow comparison](validation/meeting-2026-10-22/archived-comparison/control-regression.json)

The diagnostic viewer is a postprocessing experiment; it is **not** the default
pipeline and is not evidence of improved accuracy. Both viewers default to both
camera tracks. Source observations, projections and cross-camera associations
remain distinct and may be wrong.

The new optional `--track-candidate SEGMENT_ID` stage uses the upstream CoTracker3
implementation, seeded from an existing split-camera observation. It adds dense
image tracking and a conditional camera-local projection using an existing
calibration plus the existing camera-registration routine. It does not replace
the baseline aggregate or establish physical trajectory accuracy. No new rink
calibration is fitted by this added stage; the baseline still has its prior
calibration behavior. Handle tracking has not yet yielded reliable physical spin.

## Historical research runner (legacy routing example)

```bash
feasibility/scripts/python.sh prototype/scripts/run_throw_pipeline.py \
  --video /absolute/path/to/video.mp4 --source-id RECORDING_ID \
  --start 0 --end END_SECONDS --layout-chunk-s 90 --allow-partial \
  --output-dir /absolute/path/to/new-output --audit-source-activity
```

Replace the placeholders; use a new output directory. This invokes the existing
implementation described in the pipeline document. It does not invoke the
archived original workflow or the no-ring diagnostic. It still contains a legacy
Beijing adapter; cleanup has not changed inference or removed that code branch.

## Repository map

| Location | Role |
| --- | --- |
| `prototype/` | Current algorithms, executable scripts and tests; includes historical experiments. |
| `validation/` | Recordings, models, annotations, frozen runs and evaluation evidence. Preserve provenance. |
| `feasibility/` | Runtime wrapper/environment and earlier feasibility work. |
| `research/` | Literature, footage investigations and report builders. |
| `docs/` | Current pipeline inventory, cleanup ledger and archived documentation. |

## History and cleanup

The previous long README mixed experiments, old completion claims and launch
instructions. It is preserved as [historical documentation](docs/history/README-before-scope-cleanup-2026-10-22.md),
not current guidance. Recordings, models and previous results remain in place.
211 recording-specific leaf scripts were archived after checking source references.
Historical commands for those scripts require restoration from the archive.
The [script cleanup manifest](docs/cleanup-scripts-2026-10-22.json) records exact
paths, hashes and the recovery command. Runtime dependencies were retained.

[Cleanup ledger](docs/cleanup-2026-10-22.json): obsolete report copies and the
removed tracking-status UI were archived; disposable tool/Python caches removed.
Source data, models, labels, failures and measured results were not deleted.
