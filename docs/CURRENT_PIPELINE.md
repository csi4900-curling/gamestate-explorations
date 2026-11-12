> **10 November 2026 — current development path:** the public app is
> `./curling-workbench` (loopback port 8766). Explicit operator calibration fits
> one consistent physical camera from source rink markings. Inference reuses it
> through source-image alignment; it does not refit rink geometry from stones.
> Stone detection and ByteTrack, camera association, board/state outputs and
> synchronized viewers run through the same saved job specification. This has
> **not** passed complete-trajectory physical accuracy or identity acceptance.
>
> The user accepted provisional targets of 10 cm median and 25 cm p95 position
> error. These remain targets, not measured performance. The metric evaluator
> requires external source-bound trajectories and declared reference uncertainty;
> a camera-agreement score or source-point review cannot pass that gate.
>
> Current development evidence: CAN–SWE82–110s, job `867eeb420ea5`, verifies image
> alignment on280/280frames in both panels. Five of243trajectory samples have
> no geometry because the body box is clipped. NOR–CZE600–840s, job
> `e0e5a777b0d2`, has3provisional links and25comparable paired samples: camera
> disagreement median0.1306m, maximum0.3356m. Twelve of1414trajectory samples
> lack geometry. Foreground masking loses one usable NOR sample relative to the
> unmasked physical-camera run and costs more runtime. These inspected recordings
> are development data. See the [preserved comparison](../validation/trajectory-acceptance-2026-11-10/public-geometry-comparison.json).
>
> Runtime recovery now supports a verified interrupted detector prefix: raw
> detections can be reused, uncommitted tails are ignored, and tracking/geometry
> rerun. A supervised user service and single-store ownership lock are provided.
> A worker failure remains visible in the live API even if storage cannot save
> its state. Completed observations can rebuild downstream outputs in a separate
> development job, preserving the original run. The actual public rebuild was
> checked on CAN job `66ab57974c6d`; frozen input hashes and original outputs
> remained unchanged. This rebuilt view leaves absolute end unknown without a
> past readable marker and does not backfill future state.
>
> All calibrated hog-crossing observations are retained alongside their existing
> association hypotheses. Unassigned or competing crossings are exposed as
> unresolved camera observations, not asserted to be extra physical throws.
> The longer public run and a fresh-detection obscured-departure test are in
> progress; no outcome is claimed here. The historical audit below is preserved.

> **3 November 2026:** This is the historical audit of the 22 October routing
> path. It is not the current learned-event workbench recipe. The workbench runs
> learned stone detection + ByteTrack line crossings and board/score observations,
> OpenCLIP event colour, the shared directional aggregate, and synchronized board
> postprocessing. It does not run CoTracker/SAM over every throw or produce
> validated physical spin counts. See the current [launch instructions](../README.md#local-workbench--3-november-2026)
> and each workbench run's immutable `spec.json`, stage logs and observation protocol.

# Current executable pipeline — audited 22 October 2026

This describes the code that exists, not the intended finished system.
The split-screen path was consolidated after the inventory: the two intermediate
receiving passes are bypassed. Event detection, departure projection and final
split receiving rules are unchanged. This is a labelled development change,
not a new transfer result. A 45-second public-entry-point regression preserved
final events, segments, receiving hypotheses and links exactly. Full-match
equivalence has not yet been rerun. See [regression evidence](../validation/split-pipeline-development-2026-10-22/consolidation-regression.json). All paths below refer
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

Entry point: [run_throw_pipeline.py](../prototype/scripts/run_throw_pipeline.py).
The latest complete Sweden command is preserved in
[sweden24-timing.json](../validation/meeting-2026-10-22/runtime/sweden24-timing.json).
Those measured runs executed a frozen checkout; do not assume every future
workspace run is byte-identical. The inventory alongside this document records
current hashes and comparison with that checkout where available. At the pre-consolidation inventory, all 24 listed
implementation/reference/model files matched the measured-run checkout. The new
`split_pipeline.py`, changed dispatcher and receiving cache provenance are
recorded separately in the development freeze; the old hashes are historical. See the
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

[run_span_probe.py](../prototype/scripts/run_span_probe.py) uses
[SpanPassageDetector](../prototype/span_passage_detection.py), the colour/body
stone proposals and tracker in [throw_detection.py](../prototype/throw_detection.py).
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

[complete_throw_trajectories.complete](../prototype/scripts/complete_throw_trajectories.py)
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

### 5. General integrated tracking pass — now bypassed for split-screen

[complete_integrated](../prototype/integrated_trajectory.py) retains the departure
segments and searches the right panel from the first departure observation for
up to 40 seconds, at approximately 2 Hz. It combines a frozen linear stone-patch
SVM (`validation/curlobserver-learned-probe/model-v1/model.npz`) with colour-cap
proposals and motion association. This is not neural-network inference.

It builds motion hypotheses, samples their geometry at 1 Hz, fits house geometry
from image rings, and requires learned appearance support for accepted projected
samples. It uses camera-role/motion orientation and uniqueness/eligibility rules
to select provisional segments. Output: `tracking-evidence/aggregate.json`.

### 6. Registration-based geometry extension — now bypassed for split-screen

[extend_registered_trajectories.extend](../prototype/scripts/extend_registered_trajectories.py)
keeps the left segments, revisits the motion hypotheses, fits/propagates geometry
from nearby accepted same-shot frames with feature checks, and reselects eligible
segments. It does not simply append points to all original tracks.
Output: `registered-evidence/aggregate.json`.

### 7. Split-specific receiving — now called directly after departure projection

[complete_receiving](../prototype/split_receiving_trajectory.py) then keeps only
`left_split` segments and runs the receiving search. The new
[split_pipeline.py](../prototype/split_pipeline.py) prepares the common-rink
departure coordinates and calls this stage directly, avoiding stages 5/6.
**The accepted right-side segments from stages 5/6 are not the final right tracks.**
The intermediate hypotheses/evidence remain available, but the accepted segments
are replaced. This was redundant work in the measured baseline; the consolidation removes it
for split-screen inputs. The legacy non-split branch still uses stages 5/6.

For each candidate, use its colour and search a right-panel crop over up to 40 s
at 2 Hz. Extract cap proposals and run greedy nearest-position tracking,
respecting cuts and a 1.1 s gap limit. The configured position gate is 130×gap
pixels; it is not learned re-identification.

Fit target house ellipse/rings and hog-line geometry, initialized from the right
reference (`06495.jpg` and the refined right H), using
[source_specific_house_calibration.py](../prototype/source_specific_house_calibration.py).
[camera_geometry.py](../prototype/camera_geometry.py) can propagate accepted
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
repeated video decoding and geometry computation. The discarded intermediate
right-track passes have now been removed from the split path, but no new identity
algorithm or detector has been integrated yet. The current default still enforces the ring gate; the diagnostic has not
silently replaced it. There is no validated revolution estimator.

Next implementation work must consolidate one path and test full trajectories,
including same-colour identity, handoff, continuity and geometric accuracy, without
manual per-recording calibration. This document does not mark that work complete.
# Optional development attachment added 22 October 2026

`run_throw_pipeline.py --track-candidate SEGMENT_ID` automatically initializes
upstream CoTracker3 from an existing split-camera cap observation, in native video
pixels. It writes `spin-development/result.json` and a synchronized source-video /
camera-local projection viewer. `--spin-config` instead accepts explicitly declared
initialization data for controlled experiments, including manual handle points.

This attachment preserves the baseline aggregate byte-for-byte in the checked
45-second cached regression. Its projection stage reuses one already accepted
calibration and calls the existing `camera_geometry.transfer` routine for each
frame; it performs zero new rink-calibration fits. This does **not** remove the
baseline's existing per-candidate calibration behavior described above. Neither
dense availability nor paint registration establishes physical trajectory accuracy.
See [the deliverable](SPIN_DELIVERABLE.md) for measured results and remaining work.

The attachment also exposes the existing conditional cap-height model, initialized
once and transported by image registration. Raw projections remain available.
The final fresh automatic case has 346 raw points but zero height-adjusted points:
its inherited calibration fails the existing camera-consistency test. Another
anchor 0.5 seconds later succeeds conditionally. This is an unresolved geometry
failure, not evidence that metric trajectories are accurate. See the linked
French report for source clips, runtime and both favorable and failed outputs.

## Two-view dense development path

`run_throw_pipeline.py --track-throws` runs the same CoTracker adapter for every
nonempty split-camera segment of every event. No recording-specific inference
script or new association thresholds are introduced. Each segment is seeded
from its existing detector observation. Departure intervals still come from the old detector/tracker. Receiving
episodes now use the bounded event window described below. This does not certify
a physical stop or recover identity after complete occlusion.

The existing aggregate's cross-camera links are copied with their provisional
status; no learned re-identification is claimed. Conflicting/missing link targets,
missing camera roles and tracking failures remain explicit. A failed segment
does not erase the event or its other camera evidence. The baseline aggregate is
not overwritten with these development predictions.

Output: `two-view-tracking/index.html` and `result.json`. Both panel markers use
one source-video clock, with explicit unobserved handoff intervals. Raw and
conditional-height plots remain camera-local, avoiding an unverified common-rink
orientation. No line is drawn through unseen travel. The detailed per-segment
results remain linked from the viewer. `--throw-tracking-cache` accepts a JSON
mapping from segment IDs to existing results; source/config/weights/adapter and
point-file hashes are checked by the same cache contract.

## Collision-continuation development change

The former dense receiving configuration ended at the last legacy point, even
when that tracker disappeared at a collision. It also initialized only the
delivered point. `--track-throws` now requests a receiving-scene episode: the
same existing 40-second event budget, bounded by source end, the next detected
delivery or a known camera cut. It does not declare a physical stop when the old
track ends. Departure processing and cross-view association rules are unchanged.

The delivered seed is retained. Other queries come from the existing
`right_large_cap_proposals` implementation on the first receiving frame, using
unchanged defaults and both colours. The older body-filtered detector was tested
for initialization and missed the struck stone in the user example; that failure
is preserved. This detector choice is a development change, not independent
transfer evidence. It is not a learned detector, and proposals can be false or
miss occluded stones. No manual point, collision-specific threshold or motion
simulation is supplied. CoTracker handles each query; IDs remain provisional.

The two-view viewer now renders all queries with separate colours and preserves
visibility/geometry gaps. Receiving raw and conditional-height projections remain
separate. The completed three-case development check follows the recorded protocol in
`validation/collision-development-2026-10-22/protocol.json`; its existence alone
is not evidence that collisions are tracked correctly.


### Decoder and cache reproducibility

The first collision development runs exposed an environment mismatch: the main
pipeline used OpenCV 5.0.0.93 while the neural adapter used 4.11.0.86. At the same
source frame, small decoded-pixel differences caused the unchanged cap proposer
to omit a red stone. That failed run is retained. The tracking dependency is now
pinned to the main pipeline's version; their decoded frame was checked byte for
byte. The public runner passes its decoder-build hash to the adapter, which fails
explicitly on a mismatch. Cached tracking additionally requires identical decoded
RGB input and actual query coordinates/names. Fresh inference for the same three
preselected cases is recorded under `validation/collision-development-2026-10-22/canonical`.

### Identity after visibility loss

In the first extended run, the struck-stone query followed its initial movement
but later reacquired the delivered stone after an occlusion. That is an identity
failure. The combined viewer retains the raw predictions and marks all model-visible
fragments after a native visibility loss as identity-unverified, using dashed
lines and markers. This annotation neither repairs the switch nor establishes
that uninterrupted queries have correct identity. Query initialization still uses
only the first receiving frame, so stones missed there are not tracked later.


### Collision evaluation outcome (same development recording)

The completed three-case regression is linked from
`validation/collision-development-2026-10-22/index.html` (French).
The public primary viewer shows separate delivered/struck motions through contact,
but the struck query later reacquires the delivered stone. The additional red/yellow
collision follows both stones in the reviewed frames. The non-collision control
has 64 native-rejected delivered-stone samples, including inspected frames where
the stone is visibly unobstructed. CoTracker's upstream decision combines visibility
and tracking confidence at its unchanged 0.6 threshold. It is not an oracle for
physical occlusion. Reliable identity and complete observable coverage remain open.

The final source-clock viewer holds markers for their full frame duration, correcting
an artificial last-quarter-frame disappearance. This presentation-only revision is
recorded separately from the frozen inference; predictions were not modified.
