# Left/right pipeline: implementation and acceptance contract

User-approved scope, 22 October 2026. This is the target, not a completion claim.

## Current implementation priority

First deliverable requested 23 October 2026: process one complete left/right
match through event detection, top-view trajectories and match state (current
points and stone positions). Report stage runtime and actual measured failures.
Canada–Sweden 2024 is development footage, not an independent transfer test.
Revolution estimation follows this deliverable, not its prerequisite.

Acceptance for this deliverable requires the full public run and synchronized
viewer, event TP/FP/FN against timestamped references with reviewer provenance,
trajectory coverage and identity/gap review, both-end board observations and
score/end state with observed/inferred/unknown status. Historical event scores
cannot be reused as the learned-line pipeline's accuracy. Do not claim complete
match state from OCR totals plus unassociated detector boxes.

User clarification, 22 October 2026: first connect departure and receiving views,
then make tracking consistent, then validate clean top-view trajectories across
throws. Board/score/spin work follows this sequence. Cross-view association must
remain explicitly provisional until physical identity is evaluated; a shared
candidate ID or upstream point tracker alone does not verify the handoff.

## Product

One public video entry point and one versioned configuration for the format.
No source-ID branches, recording-specific detector rules, manually supplied new
homographies, or one-off scripts that silently become production inference.
Common modules may be added; input videos and start/end intervals are data.

Required outputs:

1. Throw events with observed start, passage and stop evidence. Exact release is
   unknown when occluded; passage time must not be called release time.
2. Persistent physical-stone identity connecting event, observations, camera
   handoff and trajectory fragments. Local track IDs are not physical IDs.
   Same-colour ambiguities, collisions and occlusions must remain explicit.
3. Timestamped observed image positions and rink positions through the observable
   delivery, travel and end-zone interval. No silent filling of missing data.
   Measured/estimated/interpolated positions must be distinguishable.
4. Board observations for BOTH physical ends, with colour, identity, position,
   last observed timestamp, visibility and stale/unknown status. Camera panel is
   not a permanent physical-end identifier; travel direction can change by end.
5. Game state: end number, team/colour mapping, deliveries, score and provenance.
   Distinguish current provisional shot count in a house from confirmed end score
   and accumulated match score. Unknown/occluded score is not zero.
6. Kinematics: velocity/acceleration only on adequate continuous calibrated
   observations, with units, sampling interval and uncertainty; no derivatives
   across camera gaps or identity switches.
7. Spin: observed handle orientation and unwrapped angular motion if supported.
   Translational position does not uniquely determine angular velocity. RK4 is a
   numerical integrator, not an estimator of missing spin. Model-inferred rotation
   must be separately labelled and validated; do not report assumed revolutions
   as measured. This is secondary to event/identity/trajectory/board reliability.
8. Synchronized viewer whose current camera markers, identity and trajectory
   selection agree, including empty outputs and explicit gaps.

## Development discipline

- Preserve a reproducible baseline and complete code/model/config/input hashes
  before inference changes. Do not compare different inputs as a regression.
- First changes: remove redundant split receiving work without changing final
  observed trajectories; record exact comparisons, not just unit-test passes.
- Improve within-camera identity next using one-to-one motion association with
  explicit ambiguity. This alone does not solve cross-camera physical identity.
- Then unify continuous two-panel decoding, track all stones (including stationary
  stones), retain shot-specific calibration, and integrate board/game state.
- Every change gets an explicit hypothesis, behavioral tests, unchanged-input
  regression and video evidence. Target-informed changes remain development.
- Full-video accuracy and runtime are measured only after full-video execution.
  A short smoke test or component test must not be described as reliability.
- Freeze before independent video evaluation. Preserve all failures. Do not add
  rules to an evaluated video and continue calling it a frozen evaluation.

## Required evaluation

Events: one-to-one timestamped reference, TP/FP/FN and timing errors.
Identity: identity switches, incorrect camera handoffs, fragmentation, unknown
assignments and coverage; evaluate same-colour neighbours and collisions.
Trajectories: observed-time coverage, gaps, end-zone coverage, geometric errors
against independent annotations, orientation and scale, endpoint identity.
Board: per-end stone precision/recall, position error, identity and staleness.
Score: exact field accuracy, timestamp/end alignment, abstention and provenance.
Runtime: per-stage wall/CPU times, decoded frames, calibration attempts/reuse;
no claim that a whole stage's duration equals homography multiplication time.
Spin: angular tracking/revolution error against independently reviewed orientation
sequences; synthetic ODE integration tests cannot substitute for this evidence.

Numerical product acceptance thresholds must be recorded before the independent
benchmark. Do not invent supervisor approval for thresholds not agreed upon.

On 10 November 2026 the user accepted provisional position targets of 10 cm
typical error and 25 cm at the 95th percentile. The engineering benchmark uses
the median for typical error. These are acceptance targets, not measured
performance. Evaluate against independent, source-bound metric trajectories;
report event misses, observable coverage, identity errors and gaps alongside
position error. Camera agreement and calibration check residuals cannot replace
this measurement.

## Explicit event-line setup exception — 23 October 2026

The user accepts manually placing the event crossing line in a GUI, provided it
is an exposed configuration rather than hidden source-specific coordinates.
This is event setup, not manual selection of homography calibration landmarks.
Automatic placement from rink geometry is a future option, not a required new
trained model or a current capability. Line position, endpoints, accepted
crossing direction and detector/tracker settings must be recorded with results.
The user prioritizes learned stone detections crossing that line and replacing
the surrounding-player-motion rejection in the new event path. Preserve the
previous span/colour detector for comparison. A stone crossing remains a
candidate until live-delivery versus collision/clearing/replay context is checked.

## Explicit camera calibration — 9 November 2026

The user now permits an exposed calibration step when there is no independently
validated learned rink-position model. The default workbench requires checked,
confirmed source calibration before starting a new metric run. This supersedes
the no-manual-homography-setup restriction above for the explicit workflow.

The operator selects an exact saved source frame for each camera, marks known
intersections or visible ring arcs and line segments, and reserves separate
check points. Ring and line samples are manual physical-feature labels. They
are fitted with the shared OpenCV/SciPy implementation; the application does
not label them as independent model detections or ground truth. A read-only
projection overlay and numerical checks are shown before confirmation. The
engineering residual limits are versioned and are not validated absolute
accuracy bounds or supervisor-approved product acceptance thresholds.

Confirmed records are immutable and source-hash-bound. Each run snapshots its
selected records and source-frame images. Explicit pose intervals must cover
the analysis interval without overlapping mappings. For an unchanged camera,
the fitted physical camera is reused. The default now measures image rotation,
uniform scale and translation with upstream OpenCV SIFT and similarity RANSAC,
using separate withheld correspondences and spatial-support gates. A pinned
upstream YOLO person-segmentation model excludes predicted foreground masks from
feature selection. Those predictions can be wrong; they do not establish rink
or stone identity. Geometry is transported through accepted source-image
alignment without fitting new rink geometry or aligning stone trajectories.
Unsupported framing changes, occlusion and insufficient visual support produce
missing geometry requiring review or another explicit pose calibration.
Calibration without longitudinal perspective
support is limited to the bounded marked image region.

The previous automatic baseline remains selectable with
`--profile prototype/config/workbench-legacy-baseline.json` for reproducibility.
It is experimental and its availability does not certify accuracy. Explicit
calibration does not solve physical identity, feed synchronization, absolute
stone-position accuracy, or the remaining full-match acceptance requirements.
