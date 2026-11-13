# Reusing established models for the left/right pipeline

Research checked 22 October 2026. This is a benchmark shortlist, not a claim
that these models are integrated or perform well on our recordings. No new model
weights have been downloaded or substituted into the pipeline in this step.

## Candidate components

| Component | Upstream implementation | Intended experiment |
| --- | --- | --- |
| Stone detection | [RF-DETR](https://github.com/roboflow/rf-detr) | Fine-tune an appropriate released detector on annotated curling frames; evaluate small/occluded stones in both panels at useful resolution. |
| Object association | [ByteTrack](https://github.com/FoundationVision/ByteTrack) | Established tracking-by-detection baseline retaining low-score evidence, replacing hand-written greedy association if benchmarked better. |
| Appearance/motion association | [BoT-SORT](https://github.com/NirAharon/BoT-SORT) | Motion, camera compensation and optional ReID baseline. Published person ReID weights are not validated stone identity features. |
| Mask propagation | [SAM 2](https://github.com/facebookresearch/sam2), [SAM 3](https://github.com/facebookresearch/sam3) | Benchmark detector-initialized mask tracking through partial occlusion. SAM 3 supports concept/text and visual prompts. Neither establishes physical identity across both views by itself. |
| Point tracking | [CoTracker3](https://github.com/facebookresearch/co-tracker) | Track selected centre/handle features and visibility through short native-rate clips. Point tracking is not automatically persistent multi-stone identity. |

ByteTrack/BoT-SORT are established baselines, not a claim of the newest overall
leaderboard result. General benchmark rankings cannot establish the best curling
model. Prefer pinned upstream implementations and one common adapter interface;
no recording-specific code or weights. Choose the production component based on
held-out match results, accuracy/identity/coverage and runtime together.

The current project used CurlObserver patches for a small classical SVM, not a
modern full detection/segmentation model. That is not an adequate comparison of
these alternatives. OpenCV remains useful for decoding, geometry and overlays;
the issue is the algorithms and validation, not the library name.

## Available curling data

The [CurlObserver dataset repository](https://github.com/CurlObserver/dataset)
describes 5,000 detection frames, oriented-box/segmentation annotations and 112
tracking clips with per-frame track IDs, including stone interactions. Verify
actual downloaded annotation coverage and source identities before selecting a
split. Its suggested random frame split is not sufficient for our across-match
evaluation: group by source match/recording and exclude test footage from tuning.

The associated [CurlObserver paper](https://doi.org/10.1016/j.eswa.2025.128745)
is directly relevant to broadcast geometry. Finding a paper/dataset is not proof
that runnable full framework code and pretrained weights are publicly available;
that availability has not been established here.

## Angular velocity and revolutions

Track a distinguishable handle/body feature at native video cadence. Correct
camera motion and perspective at the feature's height (the ice-plane homography
alone is not automatically correct for the raised handle). Estimate and unwrap
orientation theta(t); fit locally to obtain omega = d(theta)/dt. Signed net turns
are delta(theta)/(2*pi); accumulated turns use the integral of abs(omega)/(2*pi).

Symmetric handle observations can be ambiguous modulo pi; occlusions, blur and
insufficient frame rate can leave the number of turns unknown. Do not unwrap
across an unresolved gap by inventing rotations. A dynamics model may estimate
missing intervals only with calibrated parameters and explicit uncertainty.
RK4 integrates a specified ODE; it does not identify angular velocity from centre
positions. Direct measured angle differences need no RK4 integration.

[Precision kinematic measurements of curling stone motion](https://www.nature.com/articles/s41598-022-19303-4)
used video tracking of two attached labels, with parallax correction, to measure
translation and rotation. That supports video-based feasibility, but its controlled
marked-stone setup is not evidence that ordinary broadcast handles are resolved.
Our earlier 91-frame handle inspection establishes visibility in one clip, not
angular-velocity or revolution accuracy.

### Estimating gaps: research and acceptance checks

The [2022 measurement paper, full text](https://pmc.ncbi.nlm.nih.gov/articles/PMC9440934/)
reports nearly constant angular speed in some phases and accelerating rotation
in some measured shots. Do not impose universally monotonic spin decay or infer
angular speed from increased curl near the end of a trajectory.

[Leaney's 2020 smartphone gyroscope study](https://geoconvention.com/wp-content/uploads/abstracts/2020/58103-curling-rock-physics-and-smartphone-rotation-data.pdf)
compares measured rotation with friction models. Adding a pivot-related torque
improved a fit; standard kinetic friction alone missed measured deceleration.
This is evidence for comparing coupled translation/rotation models, not a
validated broadcast estimator or a ready-to-use upstream implementation.

Benchmark short visible orientation sequences at native frame rate, stratified
by early/middle/late trajectory, panel, stone size and occlusion. Measure usable
handle visibility before assuming coverage. Compare local constant-angular-speed
and angular-acceleration estimates with a fitted physical model only where its
parameters are identifiable. Use established fitting/integration libraries.
Hide observed intervals and score recovered angular speed and total turns against
the withheld observations, by gap duration and shot stage; then evaluate on
independent recordings. Include direct-observation coverage and unresolved counts.
Collisions and camera cuts require explicit treatment, not smooth extrapolation.
Report observed angles, model-estimated spans and unresolved spans separately.
Neither CoTracker's predicted hidden point nor a fitted ODE is a visible handle
measurement. A few isolated angles can leave whole revolutions ambiguous.

The newer asperity-based pivot-slide paper (doi:10.1139/cjp-2024-0305) was located,
but full-text retrieval failed in this research step; its equations and code
availability have not been verified and it is not an implemented component.

## Compute and execution status

Historical check on 22 October, superseded by the execution evidence below:
PyTorch was not installed in the project environment; no NVIDIA device
is exposed. SAM 3's official setup requires a CUDA GPU and gated checkpoint access.
Do not claim a GPU benchmark has run. Smaller CPU-compatible experiments can be
prepared, but practical detector fine-tuning and heavier segmentation benchmarking
need an appropriate environment. No remote costs or dataset uploads authorized
merely by this shortlist.

### Execution evidence added 23 October 2026

The detector environment now runs PyTorch 2.9.1+cpu and the supplied single-class
YOLO26 stone detector. The public development pipeline uses OpenVINO on the Intel
GPU for event detection; dense CoTracker remains on CPU. These are separate
backends, not evidence of CUDA availability. The reversed-direction public
regression processed 924–938 s with two successful tracking segments and no
processing failures. Its elapsed process time was 1938.13 s, including cached
detector observations; fresh CoTracker model time was 1557.46 s. This short run
does not establish full-match runtime or physical identity accuracy. Evidence:
`validation/full-match-development-2026-10-23/directional-reversed-public/attempt-0000/profile.json`
and `external-process-runtime.json` in that directory.

An isolated development comparison now reuses
[OpenCLIP](https://github.com/mlfoundations/open_clip), version 3.3.0,
`ViT-B-32 / laion2b_s34b_b79k`, to rank descriptions of red and yellow stone
handles. No HSV thresholds or colour fine-tuning were used. This is a component
candidate, not part of the frozen public pipeline.

- First set: 24/24 assistant-reviewed colour labels matched, both with manual
  crop extents and with the saved detector boxes. Ten receiving-view frames,
  repeated stones, development footage. Detector false positives and ignored
  ambiguous regions remain recorded separately.
- Second set: 37/37 readable labels matched on 39 saved detector crops. Only
  three were left-panel crops; the other 36 were right-panel crops. Two
  mixed-colour crops had unknown reference labels and still received forced
  yellow predictions. Do not interpret two-way ranking as an abstaining classifier.
- Only 10/39 second-set boxes were visually supported as individual stone
  extents; many other boxes cover overlapping stored stones or the same cluster.
  Correct colour labels do not validate stone counts, in-play status, team
  assignment or physical identity.
- Median CPU inference was 0.62 s/crop on the first detector-crop set and
  0.25 s/crop on the second. CoTracker was running concurrently; these are not
  isolated hardware timings, and per-frame use has not been justified.

Protocols, unchanged prompts, source-only colour annotations, model/package
hashes, raw similarities and failures are preserved under
`validation/full-match-development-2026-10-23/stone-colour-component/` and
`stone-colour-two-panel-component/`. Dependencies were installed separately in
`/home/user/curling-colour-deps`; the frozen public jobs were not modified.
These small same-match comparisons do not establish independent generalization.

Next benchmark: detector quality first, then association on the same detections;
compare current baseline, ByteTrack/BoT-SORT and a selected mask/point tracker on
identical annotated sequences. Include same-colour neighbours, collisions,
occlusion, camera changes and end-zone stopping. Use the shared product outputs
and metrics in LEFT_RIGHT_REQUIREMENTS.md. Preserve stage and end-to-end results.

### YOLO head comparison on preserved annotations

The supplied checkpoint defaults to the YOLO26 end-to-end, NMS-free head.
The installed upstream Ultralytics also supports `end2end=False`, selecting the
conventional head and standard NMS. This is an upstream component variant, not
a hand-written duplicate suppression algorithm. It changes predictions and is
not part of the frozen full-match run currently executing.

On the same ten previously annotated 640×360 source frames, using the same
confidence 0.1 and checkpoint input size 1280 for both heads:

| Head | Object hits | Extras | Misses | Ignored region predictions |
|---|---:|---:|---:|---:|
| Default end-to-end | 24 | 4 | 0 | 23 |
| Conventional + upstream NMS (default IoU 0.7) | 24 | 0 | 0 | 22 |

These are one-to-one centre-in-annotated-extent scores against assistant source
annotations, not independent ground truth, box IoU accuracy or event accuracy.
Ambiguous parked-stone regions are excluded explicitly. The conventional head
did not lose any of these labelled appearances; this does not establish reliable
separation of all touching stones. Median CPU call time after the first image
was 2.65 s versus 2.38 s, with concurrent full-match processing; not an isolated
runtime benchmark. The earlier detector comparison used confidence 0.25, so its
counts must not be substituted for this paired 0.1 comparison.

Evidence: `validation/full-match-development-2026-10-23/detector-head-labelled-comparison/`
contains protocol, executed adapter, raw predictions and `evaluation.json`.
Next required check: shared-input temporal association through collision and
occlusion, including duplicate initiation and missing detections. No hybrid or
production replacement has been validated by this still-image comparison.

### Constant-spin gap model: additional evidence

[Dzikowski et al., Sensors 2022](https://pmc.ncbi.nlm.nih.gov/articles/PMC8839312/)
measured stone motion with an IMU on a competitive curler's deliveries. The
reported initial angular velocities were 50–100 degrees/s; angular speed decreased
slightly for most of the shot, with most lost in the last 0.25 seconds. This supports
approximately constant spin as an initial mid-trajectory gap model, not a universal
whole-shot assumption. Murata's observed exceptions and terminal braking remain
relevant. These experimental measurements are not measurements of our recordings.

For fixed moment of inertia, I*d(omega)/dt = net torque. Zero torque implies constant
omega; low translational friction alone does not establish negligible spin torque.
Use state (theta, omega), initially d(theta)/dt = omega and d(omega)/dt = 0 with
uncertainty representing unmodelled torque. Constant-spin propagation has the exact
solution theta(t+T) = theta(t) + omega*T; RK4 adds no accuracy for this case. A
nonconstant torque model can use an established ODE solver if justified by data.

Reconnection protocol: fit orientation and angular speed from visible windows
before and after each gap, retain alternative full-turn counts (half-turn ambiguity
where handle ends cannot be distinguished), and smooth only the missing interval
using both windows. Endpoint agreement is a constraint, not independent accuracy
validation. Do not force a unique answer when multiple counts fit within uncertainty.
Do not impose smooth spin across a collision or terminal braking. Preserve observed
measurements and separate model-estimated samples in outputs.

Analytic sensitivity, not measured performance: a constant angular-speed error
of 5 degrees/s produces 25 degrees (0.069 turns) of angle error over a five-second
gap. With initial speed error bounded by e and unmodelled acceleration bounded by
A, angle error is bounded by e*T + 0.5*A*T*T, plus initial angle uncertainty.
Estimate usable gap durations from withheld visible intervals, not this illustration.
No broadcast gap-reconstruction accuracy has yet been measured.
