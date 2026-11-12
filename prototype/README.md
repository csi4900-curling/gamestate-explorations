> Current scope: one reliable left/right split-screen trajectory pipeline with stable stone identity, with explicit operator calibration now authorized when no independently reliable learned calibration exists. No per-video inference code or threshold tuning is permitted. This document includes historical work. See [the current execution inventory](../docs/CURRENT_PIPELINE.md) before using old commands or claims.

# Prototype guide

**Current entry point:** see [the project README](../README.md) and [code audit](../validation/AUDIT.md). The latest demo is [two-view linkage](cross-view/index.html). Run `scripts/validate.py` from the project root for current checks. The upload server below remains the historical image indexer.

---

# Historical milestone: observation workbench, stage 1

A runnable local video-upload and observation-review prototype. This is **not yet a video-to-game-state extractor**.

## Latest addition: original-resolution vision experiment

The [detection/calibration viewer](vision/index.html) adds source-specific analysis of 14 original-resolution frames (28 panel observations), ring calibration overlays, visible red/yellow cap proposals, a projection diagram and reference/error inspection. It is linked from the upload page and from exact matching timestamps in the full-video timeline.

On seven same-match check panel frames it matched 7 of 9 labelled visible caps, with two false proposals and two misses. This is a small AI-annotated exploratory check, not independent validation. Metric dots are **uncorrected cap projections**, not measured stone centres: handle height introduces parallax. Complete-state and simulator export remain blocked. See [the experiment README](vision/README.md) for scope, results and reproduction.

At this milestone, the combined suite contained 14 passing tests; browser checks cover the experimental viewer and its timeline integration. Arbitrary uploads still run the stage-1 indexer described below; the manually established calibration is not applied to unrelated footage.

## Open it

With the server running, open <http://127.0.0.1:8765>. The processed full-length example is at <http://127.0.0.1:8765/runs/canada-korea/index.html>.

From the project root:

```sh
feasibility/scripts/python.sh prototype/server.py --port 8765
```

The server listens on loopback only. The UI accepts local video uploads and runs indexing in a single background worker. It supports one full-frame view or two fixed side-by-side regions selected by the user. It is not a production deployment.

The generated [example viewer](runs/canada-korea/index.html) also opens as a local HTML file; the server is preferable for video seeking and browser storage. Keep its `thumbs/` folder beside it.

## What works

- Local upload → processing status → an inspectable timeline.
- Regular full-video sampling and separate left/right observations.
- Full-frame context and cropped-panel views.
- Timestamp navigation, panel filtering and heuristic review ordering.
- Local source-video playback, with HTTP byte-range seeking.
- Useful-view / occluded / wrong-view labels, browser persistence and JSON download.
- JSON observations that explicitly leave calibration, completeness and game identity unknown.
- Failure status for videos that cannot be decoded.

## Full-video run

Source: [2024 Canada–Korea wheelchair championship](https://www.youtube.com/watch?v=aWXo6XeUFQw), from the supplied catalogue. A 640 × 360 AVC indexing copy was downloaded with yt-dlp format 134. The source also offers 1080p, which should be used for later calibration and stone localisation.

- Duration: approximately 2:15:19.
- Sample interval: 10 seconds.
- Requested / decoded sample times: **812 / 812**.
- Panel observations: **1,624**.
- Sampled-frame decode failures: **0**.
- Indexing runtime on this machine: **26.27 seconds**, excluding download and browser rendering. This is one run, not a general performance benchmark.

Inspect `runs/canada-korea/observations.json` and `status.json` for the measured output.

## How to understand the implementation

1. `server.py` saves an upload, assigns a run ID, and queues a job. It serves results and seekable local media.
2. `pipeline.py` reads video dimensions/duration, requests a frame every N seconds, and splits it according to the chosen fixed layout.
3. For each region, it measures blue/green pixel fraction and image changes relative to frames one second before/after. These are cheap exploration cues, not a trained model.
4. Each observation records requested time, source-pixel rectangle, evidence image and unknown state fields. Requested versus decoded central-frame times are both retained in the sample manifest.
5. `render.py` embeds the JSON into `viewer.html`, which draws the selected panel and provides navigation/review tools. Review labels are stored in the browser and can be exported separately; they do not change an observation into a complete game state.

## Important findings from the first run

The ranking's highest entries include **empty/inactive houses**, and some include stationary people. This is expected from its paint/motion cues and demonstrates that it cannot select the active end or prove a clear board. See `evidence/top-review-candidates.jpg`. A zero changed-pixel fraction does not prove that every stone is stationary: small motions can fall below the threshold.

No claims of detection accuracy, completeness, successful shot reconstruction or centimetre precision follow from the sample counts. Sampling every ten seconds can miss short useful views. The fixed midpoint split does not discover layouts, track camera changes, handle four panels, or identify sheets/teams. Source videos with different rink colours may rank poorly. File-name/duration-based browser label keys are a prototype convenience, not a dataset identity scheme.

## Next implementation milestone

1. Use original-resolution frames to establish independent per-view calibration and validation landmarks.
2. Detect stones and retain source-pixel evidence; evaluate on manually checked frames.
3. Identify active end and settled intervals; do not mistake an empty inactive house for the match board.
4. Reconcile observations into a board snapshot only with sufficient coverage and context.
5. Introduce the Rust domain core/typestate boundaries around those evidence-backed transitions. The current Python observation format is provisional, not a replacement for that design.

## Reproduce indexing

```sh
feasibility/scripts/python.sh prototype/pipeline.py \
  prototype/sources/canada-korea-2024-360p.mp4 \
  --output prototype/runs/canada-korea \
  --profile dual_end --interval 10 \
  --source-url 'https://www.youtube.com/watch?v=aWXo6XeUFQw'
```

Dependencies are OpenCV and NumPy; the server and renderer otherwise use Python's standard library. The existing feasibility environment provides them. ffmpeg was used to create a four-second test clip, not required by the indexing CLI.

## Verification

```sh
feasibility/scripts/python.sh -m unittest discover -s prototype/tests -v
```

Six tests cover panel partition boundaries, valid sampling times, invalid options and rejection of incomplete observations at the prospective export boundary. That boundary is only a prerequisite check, not a complete curling rules validator or an implemented simulator exporter.

Browser checks exercised real-footage upload, job completion, panel filtering, sorting, panel/full-frame toggle, navigation, label persistence and JSON export, video byte ranges, and responsive layouts at 390/760px. The full-video viewer was also checked. Results are in `evidence/`.

Media remains a local research copy with source rights unchanged. No external publication or spreadsheet edits were performed.

### Continuous passage processing

[Continuous demo](http://127.0.0.1:8765/continuous/) plays a 90-second original-resolution clip with synchronized detections, camera-local provisional tracks, and partial board projections. See [method and limitations](continuous/README.md). This runs detection twice per second across the entire passage. It is source-specific; generic uploads still perform indexing. Metric stone centres and complete game reconstruction remain unfinished.

### Metric ice-plane rectification

[Rectification experiment](http://127.0.0.1:8765/rectification/) now shows actual 30-fps top-down ice video for both cameras. Ring-boundary refinement, withheld paint checks, per-frame optical flow and explicit unavailable frames are implemented in `rectification_core.py`. See [method, measurements and reproduction](rectification/README.md). The warp corrects the ice plane; stone height distortion remains unresolved and these images are not accurate stone-centre estimates.

### Stone-position accuracy benchmark

[Measured stone accuracy](http://127.0.0.1:8765/stone-accuracy/) runs the unchanged colour-cap detector on existing manually calibrated Olympic frames and compares against published diagram positions. In nine primary frames it detects 4/48 visible house-stone observations, misses 44, and produces four false house-region proposals. The four matches are all in one oblique frame, with 54.60 cm position RMSE. No overhead target is detected. This is a different-source, supplied-calibration benchmark—not accuracy measured on the Canada–Korea clip. [Protocol, caveats and reproduction](stone-accuracy/README.md).

### Body detection and conditional height-aware localization

[Replacement model](http://127.0.0.1:8765/body-localization/) adds geometry-conditioned body-outline detection for high-angle views and conditional height correction for low-angle proposals. Development benchmark: 46/48 targets detected, 2 misses, no false proposals in the scored region, and 40/48 detected within 10 cm of diagram references. The same four oblique stones improve from 54.6 cm to 7.5 cm RMSE. This is not held-out accuracy. The continuous clip now shows conditional ground estimates and assumption sensitivity; it still lacks independent metric truth. [Method, assumptions and reproduction](body-localization/README.md). The original failed baseline and frozen labels remain intact.

### Continuous throw-passage and intent feasibility experiment

[Throw analysis](http://127.0.0.1:8765/throw-analysis/) processes a continuous 18.5-minute end. The source-specific detector finds 16/16 AI-annotated outgoing stone passages, with no additional events. Eight development deliveries and eight subsequent same-end check deliveries are reported separately. This is not independent or cross-recording reliability, and timestamps mark passage through an image gate rather than release. One receiving-view example links a stable broom candidate and a provisional stone outcome; intended destination and shot-success score remain unknown. [Method and limitations](throw-analysis/README.md). The generic upload path remains an indexer.


### Learned detector integration (development, 23 October 2026)

The existing public `run_throw_pipeline.py --track-throws` entry accepts
`--stone-detector-checkpoint PATH`. With this option it selects `.venv-detector`
by default (an explicit alternative `--spin-python` remains supported). The
isolated environment contains Ultralytics 8.4.95, CPU PyTorch 2.9.1, and the same
pinned upstream CoTracker commit as the baseline. Exact installed versions are
recorded in `validation/learned-pipeline-development-2026-10-23/environment-lock.txt`.
The externally shared checkpoint is not included in git; its SHA is recorded
in the run and original detector comparison.

The option replaces additional scene-query initialization and end-snapshot
stone proposals with learned detections in the same pipeline. It does **not**
yet replace the original throw-event detector, event cap anchor, cross-view
association, or infer team colour. The detector's body-box centres are distinct
from cap queries: they use the existing conditional 0.068m body-centre height
assumption, not the 0.136m cap-plane assumption. Neither box-centre height nor
metric accuracy is verified from this footage. Missing/occluded stones at the
initial frame are not automatically initialized later in the episode.

For a frozen event aggregate, the same dense stage can be run directly:

```sh
CURLING_PYTHON="$PWD/.venv-detector/bin/python" feasibility/scripts/python.sh \
  -m prototype.spin.throws --video VIDEO --aggregate AGGREGATE \
  --output NEW_OUTPUT --checkpoint models/cotracker3/scaled_online.pth \
  --stone-detector-checkpoint research/shared-stone-detector-2026-10-22/stones_v4.pt
```

This preserves earlier outputs. Scene queries are initialized from learned
boxes; the existing event cap anchor is retained. Multiple boxes containing
that anchor are recorded as ambiguous rather than chosen by a new distance
threshold. Boxes do not establish physical identity or score. Query gaps and
unverified reacquisitions remain in the viewer.

### Configurable projection heights

For dense two-view trajectories and the receiving board snapshot, pass
`--projection-config prototype/config/projection-heights.json` together with
`--track-throws` to `prototype/scripts/run_throw_pipeline.py`, or pass the same
configuration directly to `python -m prototype.spin.throws`.

The JSON maps `cap_with_body_support` and `body_box_center` to feature heights in
metres (defaults 0.136 and 0.068). Omitted keys retain those defaults. Values must
be finite and nonnegative. These represent assumed heights of tracked image
features, not a claim that bounding-box centres are physical half-height points.
The resolved settings are saved in segment configurations, trajectory projection
metadata and board metadata; the supplied file hash is saved in the run result.
They do not change the legacy event detector or its preliminary aggregate geometry.
No GUI has been implemented. Existing runs remain unchanged.

### Learned stone crossing events (development, event stage only)

Open [the line setup page](line_gate_editor.html), choose a local video, pause at
a useful frame and click the two line endpoints. Download `line-events.json` and
`bytetrack.yaml` together. The coordinates are normalized to the full source
frame, not a fixed 640×360 ROI. Directions are relative to endpoint order. The
example JSON in `config/line-events.example.json` uses the old virtual line's
location for regression experiments; it is not automatically chosen for videos.

```sh
CURLING_PYTHON="$PWD/.venv-detector/bin/python" feasibility/scripts/python.sh \
  prototype/scripts/run_throw_pipeline.py \
  --video /path/to/source.mp4 --source-id your-source-id \
  --start 0 --end VIDEO_DURATION_SECONDS --output-dir /path/to/new-output \
  --events-only --event-line-config /path/to/line-events.json \
  --stone-detector-checkpoint research/shared-stone-detector-2026-10-22/stones_v4.pt
```

This mode uses the existing learned detector and upstream Ultralytics ByteTrack.
Detector confidence 0.1 keeps the upstream low-confidence association inputs;
the copied YAML contains explicit, editable upstream defaults, not newly learned
or video-tuned values. All sampled frames are processed; the old layout-window
routing, colour rules, motion-area veto and speed/span thresholds are bypassed.
The crossing uses observed detection-box centres associated by ByteTrack, not
its predicted hidden positions. No crossing is inferred across a missing
observation. Each tracker ID can emit once per line; ID fragmentation may still
produce duplicates, and different lines are not merged into physical events.
The source-clock viewer shows the configured line and the observed crossing
bracket. It labels the interpolated timestamp separately from unknown release.

The mode deliberately requires `--events-only`: body-centre crossings are not
yet connected to the legacy cap-specific trajectory/colour-handoff stages.
The previous dense-trajectory path remains available unchanged. Fixed image
lines do not compensate camera movement; automatic line placement, physical
identity, delivery-versus-clearing classification and full-match accuracy remain
unverified. This is a shared configurable implementation, not a script per video.
# Full-match observation integration (development, 23 October 2026)

The learned-line public mode accepts `--match-state-config
prototype/config/match-observation.example.json`. This adds conditional
height-aware board observations and RapidOCR scoreboard totals to the same
decoded samples. `match-observations.html` synchronizes both camera overlays,
separate camera-local board plots, source time and last-observed scores.

This is an intermediate observation stage, **not the finished full-match
deliverable**. It does not connect learned events to dense CoTracker episodes,
verify cross-view physical identity, distinguish every stored stone from an
in-play stone, or extract the current end. Unknown totals are not zero; stale
readings carry their observation age. Raw outputs and geometry failures remain.
The original reference calibration and existing registration/height correction
are reused; original AI-selected reference landmarks are recorded as such.

Scoreboard OCR uses `rapidocr==3.10.0` and `onnxruntime==1.31.0` in the detector
environment. The example configuration explicitly exposes team text labels,
OCR crop, sampling interval, reference resources and feature heights. Its
CAN/SWE labels are match metadata, not inferred team/stone identity.

The same OCR stage supports resumable full-recording inspection:

```sh
CURLING_PYTHON="$PWD/.venv-detector/bin/python" feasibility/scripts/python.sh \
  -m prototype.scoreboard_observation --video /path/to/source.mp4 \
  --config prototype/config/match-observation.example.json --output /new/output
```

Resume requires unchanged source, config, parser, OCR packages and model hashes.
This command measures the OCR stage only, not whole-pipeline performance.

`--detection-cache /previous/event/run` can reuse saved learned detections when
the source, model/runtime, detector adapter, decoder build and confidence match
exactly. It reconstructs ByteTrack state normally and reports reused frames and
prior inference time separately. Use a new output directory; interrupted outputs
are preserved. A 20-frame public-entry replay reproduced detections and tracker
observations exactly. Older caches without decoder provenance are rejected.

`--tracking-progress-dir /persistent/progress` on the public `--track-throws`
entry point saves upstream online CPU CoTracker state after each completed
window. Restart into a new output directory with the same progress directory.
Reuse requires identical decoded pixels, queries, weights, adapter, upstream
code and runtime settings. Changed inputs create a different checkpoint key;
existing predictions are not treated as interchangeable. Decode, geometry and
report generation still run. This option does not improve identity accuracy.
Checkpoint write time and resumed window offset are recorded separately.

`match-observation-stable.example.json` selects the explicit development geometry
repair: original native-resolution departure registration, and the original
automatic receiving house/hog initializer followed by anchor registration reuse.
It retains the initializers' existing heuristics; it is not learned geometry or
proof of metric accuracy. The earlier direct low-resolution registration mode
and its failures remain preserved for comparison.

The public learned path also accepts `--track-throws` instead of `--events-only`,
with `--match-state-config prototype/config/learned-two-view-development.example.json`.
This explicit development configuration supplies broadcast camera roles and the
`unique_temporal_hog_crossing_development` handoff hypothesis. It connects typed
body-centre tracks to the existing CoTracker runner and carries configured feature
heights through both stages. Receiving tracking uses the observed learned track
extent, not the legacy cap pipeline's 40-second episode budget. The new handoff
is programmed temporal association, **not learned re-identification**: ambiguous
incoming crossings remain ambiguous, and a unique link remains provisional.

The linked dense viewer uses the same source clock for camera-local trajectories,
both-camera board observations and last-observed OCR totals. These are camera
panels, not verified physical-end identities. Current end and points currently
lying remain unfinished. Full-match and physical-identity accuracy are not yet
established by the short integration checks.

### Optional learned colour evidence on end snapshots

The public `scripts/run_throw_pipeline.py` entry point accepts
`--stone-colour-config prototype/config/stone-colour.example.json` with
`--track-throws` and `--stone-detector-checkpoint`. The tracking Python environment
needs `requirements-colour.txt`. Configure `cache_dir` to reuse downloaded weights;
`null` uses the upstream cache location. The existing isolated development setup
uses `PYTHONPATH=/home/user/curling-colour-deps` and the cache
`/home/user/curling-colour-model-cache`.

This option runs the maintained OpenCLIP model on the end snapshot's detector
boxes and the exact-frame saved boxes of both panels. `colour_evidence` records
ranked predictions and cosine similarities; existing verified-colour/team/identity
fields and positions are not replaced. The viewer colours points as hypotheses.
Grouped, mixed-colour or occluded boxes can be wrong. This does not establish
complete stone counts, team assignments or points in the house.

The default remains disabled. Development evidence is in
`validation/full-match-development-2026-10-23/learned-colour-integration-development/`:
39-crop implementation parity and a saved-source public snapshot/viewer regression.
The latter replays saved detections and positions and performs fresh colour inference.
An additional public CLI integration run on source 724–736 s includes fresh receiving
tracking and colour inference, cached event detections and departure tracking, and
browser verification. Its snapshot is during motion, not a settled board. The source
review found a delivery-stick false detection with a forced colour prediction and
grouped stone boxes; readable crop-colour agreement does not establish board accuracy.
Neither test is a full-match result. The frozen full-match benchmark is unchanged.

### Inspecting upstream identity fragmentation

`python -m prototype.tracker_association_trace --reference RUN --output TRACE.json
--start START_SECONDS --end END_SECONDS --track-ids ID [ID ...]` replays saved
detections through upstream ByteTrack and records its association costs for selected
local IDs. It verifies every replayed `(track ID, detection index)` pair against the
saved run before accepting the diagnostic. It changes no associations or thresholds.
The trace exposes first-stage/unconfirmed costs; it does not record low-confidence
second-stage costs and does not establish physical identity through occlusion.

`python -m prototype.tracker_component_comparison --reference RUN --video VIDEO
--output NEW_DIRECTORY` compares upstream ByteTrack and default BoT-SORT on identical
saved detections. `--allow-partial` explicitly permits a committed immutable prefix
with `progress.json`; it remains labelled incomplete. The comparison first requires
exact ByteTrack replay. Default BoT-SORT here has no appearance ReID and applies its
camera-motion compensation to the full split-screen image. Evaluation must inspect
physical continuity and incorrect assignments, not just count local track IDs.
Use `--candidate ocsort` to compare the installed upstream OC-SORT defaults instead.
This option does not modify detector inputs or the public pipeline; differences
between upstream default configurations are part of the comparison and must be
reported rather than described as an isolated algorithm ablation.

### Optional offline scoreboard layout inference

The evidence assembler `python -m prototype.match_state_timeline` accepts
`--score-layout-memory` (disabled by default). Its usual `--run`,
`--score-observations`, `--output`, and `--teams` arguments still identify the
immutable public observations and scoreboard source. The public video entry point
`scripts/run_throw_pipeline.py` also accepts `--score-layout-memory` with learned
line events and `--match-state-config`. It writes `match-state/timeline.jsonl`
and includes separately labelled offline score inference in the synchronized
match viewer. The event scan's original score evidence remains visible.

The option uses previous directly observed TOTAL/team token boxes to infer the
layout of current numeric readings with OpenCV, then applies the existing offline
chronological score inference. It preserves direct OCR, layout predictions and
their provenance separately. Inferred fields never update the layout reference.
Chronology uses future observations, and neither stage verifies physical end
identity or points currently lying in a house. OCR numeral errors remain possible;
the layout method does not recognize or correct digits itself.
