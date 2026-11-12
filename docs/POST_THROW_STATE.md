# Post-throw state development

This addition replays saved public-pipeline observations. It does not replace or
rerun the detector, tracker, event rules, geometry or trajectory association.
Canada–Sweden 2024 is development footage. Norway–Sweden remains reserved until
the complete pipeline has been verified and frozen again.

## Executable entry point

Install `requirements-state.txt` in a development environment with the existing
NumPy, SciPy, scikit-learn and OpenCV dependencies. The recorded experiment uses
an isolated `/home/user/curling-state-deps` target directory.

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
PYTHONPATH=/home/user/curling-state-deps:/home/user/curling-project \
feasibility/scripts/python.sh -m prototype.scripts.finalize_full_match \
  --video validation/full-match-development-2026-10-23/source-1080p.mp4 \
  --run-dir validation/full-match-development-2026-10-23/directional-full-match/attempt-0014 \
  --output-dir /tmp/curling-post-throw-new-output \
  --post-throw-aggregate validation/full-match-development-2026-10-23/final/aggregate-rink.json \
  --post-throw-config validation/post-throw-state-development-2026-10-26/state-config.json \
  --event-colours validation/full-match-development-2026-10-23/final/event-colours.json \
  --post-throw-timeline validation/full-match-development-2026-10-23/final/state-timeline.json
```

This single assembly command fits the motion model once, then creates the state
review output. `--post-throw-motion PATH` explicitly reuses a matched fitted
result. With the replay argument, the model is saved in `OUTPUT-motion` beside
the requested output. Existing output/model directories are never overwritten.
Without `--post-throw-aggregate`, the normal full-match finalizer can also add this
stage using the same configuration after its aggregate and timeline are built.
This is assembly integration, not yet a verified new video-to-result inference
run with the additional stages.

## What produces each field

- Motion: upstream `hmmlearn.hmm.GaussianHMM`, two populations fitted separately
  to each panel's apparent body-widths/second. Lower-mean state is a stationarity
  hypothesis. Model settings, fitted distributions and transition probabilities
  are recorded. Offline fitting/decoding uses future observations. Camera motion
  is not newly compensated here.
- Review timestamp: programmed midpoint of the longest contiguous low-motion
  interval after observed motion, bounded by the next event candidate. Gaps split
  intervals; absent motion transitions produce an unresolved candidate. This
  selection policy is a development hypothesis, not a learned stopping rule.
- Duplicates: upstream `cv2.dnn.NMSBoxes` on saved boxes with configurable IoU
  0.7, inherited from Ultralytics. This threshold is a disclosed default, not a
  learned optimum. Suppressed observations and points before/after are retained.
- Stone groups: existing receiving-track association and OpenCLIP event-crop
  colour rankings. A tracker ID is not physical identity. Unknown stones are
  not assigned a group. Team/colour mapping is supplied metadata.
- Positions: unchanged saved height-adjusted local metric projections. This stage
  does not validate their physical error.
- Conditional visible points: `house_points.points_lying`, using physical house
  and stone radii from configuration. Missing tracks and unverified in-play
  membership remain explicit. A proposal does not authorize a post-throw score.
- End context: existing observed/inferred timeline, including its provenance.
  Missing receiving tracks retain their last source position, frame and age.
  These stale positions are drawn dashed, never substituted for current positions.
  Current raw observations suppressed by NMS remain distinguished from tracks
  actually absent from the current observation.
  Inferred end epochs avoid accumulating earlier-end IDs; they can be wrong
  when event counts are wrong. No new official end labels are inferred.
- Match totals: original OCR values with observation timestamps/age, separate
  from house points. They are not newly confirmed scores.
- Source image: exact decoded source-frame index, both camera panels intact.
  Both top-view plots share one metric scale. Off-display stones are counted,
  not silently discarded from the JSON evidence. The board now follows the
  presented source frame using every saved board observation (10 Hz in this run),
  without interpolating missing detections. Static proposal snapshots remain
  separate links. Earlier static-only viewers are preserved as superseded outputs.
  A projection selector compares the existing height-adjusted and uncorrected
  ice-plane coordinates; it does not refit geometry. Conditional points are hidden
  in ice-plane mode because they were calculated with height-adjusted positions.

## Angular observations

`python -m prototype.spin.observability` exports native detector crops and source
context at reproducible moving-track samples. `prototype.spin.handle_localization`
is an isolated component trial of maintained Transformers Florence-2 referring
segmentation, using fixed prompts, immutable model revision and recorded weights.
It does not run as a production angular estimator.

A handle mask alone is not a pair of physical, horizontal angular landmarks.
Perspective, grip height, occlusion, tracking identity and whole-turn ambiguity
must be verified before integrating angular velocity. Physical revolutions remain
unknown. Existing constant-angular-velocity gap integration is not evidence that
these angular inputs have been obtained.

## Verification boundary

Tests exercise motion-gap boundaries, ambiguous/missing state, upstream duplicate
suppression, scoring semantics, source decoding and the public assembly CLI.
Actual full-match replay and browser checks are saved beside the development
output. None of these replace independently reviewed complete board/identity
labels, settled-state timing or physical trajectory/spin measurements.
