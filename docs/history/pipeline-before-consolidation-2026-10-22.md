# Current executable pipeline — audited 22 October 2026

This describes the code that exists, not the intended finished system. No
inference change was made during this inventory/cleanup. All paths below refer
to the current workspace. This is the modified integration, NOT the original
Canada–Korea workflow. It has not met the reliability objective.

## Scope and identity requirement

One pipeline for left/right split-screen broadcasts, without per-recording
manual calibration or rule tuning. Stable stone identity must connect detections,
track fragments and camera views; multiple stones of the same colour must not be
silently substituted. Ambiguous identity must be explicit. Evaluation needs
identity errors, continuity/coverage and geometric error, not just event scores.
This is a requirement, not a description of an implemented identity solution.

## What runs

Entry point: [run_throw_pipeline.py](../../prototype/scripts/run_throw_pipeline.py).
The latest complete Sweden command is preserved in
[sweden24-timing.json](../../validation/meeting-2026-10-22/runtime/sweden24-timing.json).
Those measured runs executed a frozen checkout; do not assume every future
workspace run is byte-identical. The inventory alongside this document records
current hashes and comparison with that checkout where available. All 24 listed
implementation/reference/model files match the measured-run checkout. See the
[inventory](current-pipeline-inventory-2026-10-22.json).

`prototype/pipeline.py` is a separate coarse video indexer, not this trajectory
runner; its module documentation explicitly says it infers no stone positions.

### 1. Source verification and layout routing

Hash the input, enforce the reserved-evaluation-source exclusion, inspect sparse
layout frames (every 10 seconds on a full recording), and group routing windows.
The CLI default window is 300 seconds; the measured runs used 90 seconds.
With `--allow-partial`, supported spans are processed and unsupported spans are
retained as coverage gaps. This is not an exhaustive visibility check.

The runner still dispatches to `split_2024` or `beijing_2022` adapters. Beijing is
outside the new priority scope, but its branch has NOT been removed. A future
split-only interface remains to be implemented; no scope-enforcement claim here.

### 2. Split-screen departure proposals, approximately 10 Hz

[run_span_probe.py](../../prototype/scripts/run_span_probe.py) uses
[SpanPassageDetector](../../prototype/span_passage_detection.py), the colour/body
stone proposals and tracker in [throw_detection.py](../../prototype/throw_detection.py).
Frames are normalized to 640×360. Search region: x=40..280, y=4..116 in the left
panel. This is a restricted proposal region, not whole-rink tracking.

Red/yellow cap shape and neutral-body evidence propose stones. The underlying
tracker associates same-colour detections using motion prediction and Hungarian
assignment with distance/gap limits. The span adapter emits sustained, sufficiently
long, direction-consistent motion in either image direction. **A fixed virtual
line crossing is not required.** Stored `crossing_time_s` is the observed track
midpoint, not release time. Existing observations continue only while tracked.

### 3. Candidate confirmation and camera diagnostics

`measure_passage_motion_context.py` compares frames 0.25 s before/after the
candidate midpoint. `span_context_confirmation.py` retains candidates within
x=160±60, rejects more than 1,250 changed pixels in the nominal 80×80 neighbourhood
(intensity difference at least 24), and suppresses nearby same-colour/direction
duplicates within 10 seconds. These are development-fitted heuristics, not a
learned player/throw classifier.

Raw proposals and withheld reasons are retained separately. Candidate camera
motion is recorded as a sidecar; it does not itself supply the final trajectory.
The confirmed span outputs are assembled into `timeline.json`.

Optional `--audit-source-activity` computes panel activity and overlays blind
coverage; it was enabled for the measured Sweden run. The many additional
right-view/board flags in the runner are opt-in, NOT enabled by that command.

### 4. Initial departure projection

[complete_throw_trajectories.complete](../../prototype/scripts/complete_throw_trajectories.py)
first calls its non-integrated path when events contain observed departure points.
It uses the continued detector track where available. It splits excessive gaps
or jumps and bounds identity continuation (30 seconds). It samples at 2 Hz,
including the final point.

For each sample: decode/resize to 640×360, enlarge to 1920×1080, register against
the calibrated left reference via SIFT/RANSAC, validate ring geometry, check rink
bounds, then project the saved pixel position. Reference inputs are
`prototype/vision/annotations/calibration.json`,
`prototype/rectification/calibration.json` and `prototype/vision/frames/00750.jpg`.
Output: `departure-evidence/aggregate.json`.

This is NOT the archived native-resolution re-detection and conditional height
correction. Its added ring gate can reject points even when registration succeeds.
It also does not extend tracking outside the proposal detector's observations.

### 5. General integrated tracking pass

[complete_integrated](../../prototype/integrated_trajectory.py) retains the departure
segments and searches the right panel from the first departure observation for
up to 40 seconds, at approximately 2 Hz. It combines a frozen linear stone-patch
SVM (`validation/curlobserver-learned-probe/model-v1/model.npz`) with colour-cap
proposals and motion association. This is not neural-network inference.

It builds motion hypotheses, samples their geometry at 1 Hz, fits house geometry
from image rings, and requires learned appearance support for accepted projected
samples. It uses camera-role/motion orientation and uniqueness/eligibility rules
to select provisional segments. Output: `tracking-evidence/aggregate.json`.

### 6. Registration-based geometry extension

[extend_registered_trajectories.extend](../../prototype/scripts/extend_registered_trajectories.py)
keeps the left segments, revisits the motion hypotheses, fits/propagates geometry
from nearby accepted same-shot frames with feature checks, and reselects eligible
segments. It does not simply append points to all original tracks.
Output: `registered-evidence/aggregate.json`.

### 7. Split-specific receiving replacement — final receiving output

[complete_receiving](../../prototype/split_receiving_trajectory.py) then keeps only
`left_split` segments from the preceding result and runs another receiving search.
**The accepted right-side segments from stages 5/6 are not the final right tracks.**
The intermediate hypotheses/evidence remain available, but the accepted segments
are replaced. This is real redundant work in the current implementation.

For each candidate, use its colour and search a right-panel crop over up to 40 s
at 2 Hz. Extract cap proposals and run greedy nearest-position tracking,
respecting cuts and a 1.1 s gap limit. The configured position gate is 130×gap
pixels; it is not learned re-identification.

Fit target house ellipse/rings and hog-line geometry, initialized from the right
reference (`06495.jpg` and the refined right H), using
[source_specific_house_calibration.py](../../prototype/source_specific_house_calibration.py).
[camera_geometry.py](../../prototype/camera_geometry.py) can propagate accepted
geometry through verified same-shot registration within a 3 s anchor age.
Check projected bounds and stone width. Require an observed incoming hog-line
crossing. Select only a unique eligible track; truncate after detected stability
with the pre-approach exception in code. Ambiguous/missing tracks remain failures.

### 8. Cross-camera identity and aggregate

`link_segments` in `integrated_trajectory.py` links associated segments only when
colour matches, an incoming hog crossing is observed, forward time is within
35 s, longitudinal movement is plausible and lateral displacement is at most
2 m; require a unique possible receiver. Duplicate-assignment checks also run.

**There is no learned stone re-identification model and no validated persistent
physical identity across the match.** Candidate IDs and segment IDs are bookkeeping.
The current links explicitly say `provisional_geometry_and_colour_link`.
Same-colour stones, collisions, occlusions and broken tracks can defeat these rules.
No interpolation is made across missing travel. Final output: `aggregate.json`.

## The three outputs that must not be conflated

| Output | Meaning |
| --- | --- |
| `runtime/` | Completed public-run integration, including departure ring rejection. |
| `runtime-no-ring/` | Diagnostic postprocessing of saved accepted registrations: restores departure samples rejected solely by the ring gate. Receiving calibration and associations unchanged. NOT the default runner. |
| `archived-comparison/` | Separate reproduction/test of the original workflow, on the fixed 18.5-minute interval. NOT the current public-run implementation. |

All three are under `validation/meeting-2026-10-22/`. Viewers are generated reports
from saved results; they do not run detection during playback. Both-views mode
shows observations from all retained camera segments near the current video time.
Individual camera selection changes presentation only. The removed tracking-status
overlay is not active.

## Original workflow differences and unresolved work

The archived workflow used virtual-line events, native-resolution re-detection,
reference registration, conditional height correction, original receiving tracking
and original association. The current version changes those choices. In particular,
its per-sample departure ring gate was not called by the original departure script.

Current weaknesses: restricted departure coverage, sparse projection, asymmetric
camera processing, provisional identity, target-frame calibration fragility,
repeated video decoding and geometry computation, and discarded intermediate right
tracks. The current default still enforces the ring gate; the diagnostic has not
silently replaced it. There is no validated revolution estimator.

Next implementation work must consolidate one path and test full trajectories,
including same-colour identity, handoff, continuity and geometric accuracy, without
manual per-recording calibration. This document does not mark that work complete.
