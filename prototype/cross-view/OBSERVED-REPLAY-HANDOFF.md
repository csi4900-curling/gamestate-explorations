# Piecewise observed replay handoff

The [machine-readable handoff](piecewise-observed-replay.json) exports all **16** Canada–Korea end-three provisional throw links as separate departure- and receiving-camera trajectory segments in the same **conditional** rink coordinate convention. It contains **791 source-observed positions**. It is suitable for drawing a time-indexed evidence replay with a visible break between camera segments; it is **not** a continuous physical trajectory or physics-simulation input.

The exporter preserves the actual observation seam. Fifteen candidates have an unobserved processing gap of **5.2–9.4 s** between the last departure and first accepted receiving point. T11's expanded receiving probe supplies a first point at the same source time as its last departure point, but their nominal projections disagree by **0.613 m longitudinally and 0.091 m laterally** (0.619 m total). The record keeps both points and marks the disagreement. No cross-camera point is interpolated, shifted or fused. The T11 far-range receiving samples retain their `range_expanded_diagnostic` scope.

The handoff attaches **12** candidate visual-stability outcomes and the saved interaction cues without promoting either to a verified physical settle or collision. All rows leave release time, physical settle time, spin, complete post-throw board, metric accuracy, cross-view physical identity and simulation readiness unknown or false. These missing quantities matter: a coaching replay may show what was observed, but a physics simulator cannot infer a unique full throw from the current video outputs.

Rebuild with:

```sh
feasibility/scripts/python.sh prototype/scripts/export_piecewise_observed_replay.py \
  --cross-view prototype/cross-view/results.json \
  --source-meta prototype/throw-analysis/source.json \
  --provenance prototype/cross-view/provenance.json \
  --video prototype/throw-analysis/end3.mp4 \
  --segments-dir prototype/throw-segments \
  --departure-dir prototype/cross-view \
  --output /tmp/piecewise-observed-replay.json
```

The exporter verifies the source-video SHA-256, each per-throw segment and each selected departure observation against the saved provenance, refuses overwrite, checks chronological observations, and checks T11's reported seam against its underlying positions. A future visualizer can play each segment at its source timestamp and leave the gap empty. A future simulation gate must separately establish event identity, complete settled state, metric geometry and physical dynamics rather than treating a successful replay export as validation.
