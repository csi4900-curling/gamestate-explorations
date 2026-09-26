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
