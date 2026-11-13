# Earlier departure gate study — 28 September 2026

**Do not move the production baseline gate yet.** Earlier crossings are a useful
operational definition of a delivery, but earlier visibility must first improve.

Same full development interval (1650–2760 s), same 10 Hz frames, proposals, ROI,
association and motion checks; only `PassageConfig.gate_y` changes. The detector
core and archived predictions remain unchanged. Larger y is earlier on this view.

| Gate y, normalized 640×360 frame | Emitted events | Original tracks retained | Other tracks emitted | Median earlier crossing on retained tracks |
| --- | ---: | ---: | ---: | ---: |
| 60, archived baseline | 16 | 16 | 0 | 0 s |
| 75 | 7 | 6 | 1 | 0.520 s |
| 90 | 2 | 1 | 1 | 0.967 s |

The y=60 run exactly matches archived track IDs, crossing times and trajectories.
Other-track emissions are not independently labelled false positives. Original
track non-emissions are baseline disagreements, not independent recall estimates.
The timing gains apply only to retained tracks, not all throws. This study uses
no new gate annotations and cannot evaluate exact timing at the alternative gates.
`results.json` is the initial run; `final-results.json` repeats after formatting
with the current runner hash. Both retain full trajectories and provenance.

## Why a gate change is insufficient

The existing detector requires six observations, 24 px of displacement and a
supported crossing with observations more than 5 px on either side. Many tracks
start too late to support an earlier crossing under those unchanged rules.
People/equipment occupy the earlier region. Moving a gate does not add evidence.

Full track history is already retained before confirmation, and tracking continues
after it. Moving the trigger therefore does not extend those matched tracks or
reduce the gap between the departure and receiving cameras. Keep three different
times: first observed, gate crossing, and confirmation. Release stays unknown.
The demos leave the camera gap explicit; they do not interpolate it today.

## Next detector experiment

Improve early-view stone visibility/association on development footage; then test
an early provisional crossing confirmed by sustained outgoing motion downstream.
Backdate only to an observed bracketed crossing. If no early crossing is observed,
fall back to the later supported gate and preserve the missing prefix. Evaluate
non-throw movements, occlusions and false confirmations before adopting it.
Extending the *last* reliable departure observation and the *first* reliable arrival
observation is the separate task that can reduce the cross-camera gap.

Freeze the chosen rule before inference on the reserved event. Do not transfer
pixel y coordinates to a new camera without explicit setup.

```sh
feasibility/scripts/python.sh prototype/scripts/compare_departure_gates.py \
  --output /tmp/new-gate-study.json
```
