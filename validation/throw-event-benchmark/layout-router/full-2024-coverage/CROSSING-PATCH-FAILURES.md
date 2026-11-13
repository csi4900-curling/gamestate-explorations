# What the recovered Scotland tracks actually follow

The ten [new bridge review candidates](scotland24-bridged-development/bridge-review-triage.json)
were chosen by the detector, so this is a **prediction-targeted development
inspection**, not an independent accuracy reference. The
[crossing crop sheets](scotland24-bridged-development/crossing-source-crops/manifest.json)
show source pixels at the interpolated tracked crossing location and ±0.2 s.
The yellow crosshair marks that location. The full
[source panels](scotland24-bridged-development/new-event-source-review/manifest.json)
show camera and play context.

| Candidate | Source pixels at crossing | Frozen patch positives / matched frames |
| --- | --- | ---: |
| S56 yellow, 2093.47 s | A yellow-capped stone moving on ice | 3 / 3 |
| S58 red, 2102.30 s | Red maple-leaf logo on a moving Canadian jersey | 1 / 3 |
| S59 red, 2142.92 s | A red-capped stone moving on ice | 3 / 3 |
| S63 yellow, 2298.41 s | A yellow-capped stone moving on ice | 3 / 3 |
| S117 yellow, 4528.06 s | Crossing is partly hidden by a player; stone association uncertain | 1 / 2 |
| S156 red, 6147.40 s | A moving player occupies the crossing, no red stone at that point | 0 / 1 |
| S160 yellow, 6204.46 s | A yellow-capped stone beside a player | 3 / 3 |
| S181 red, 7022.82 s | A red-capped stone moving on ice | 3 / 3 |
| S184 red, 7062.88 s | A moving player occupies the crossing, no red stone at that point | 3 / 3 |
| S191 red, 7101.43 s | Wheelchair hardware below a moving player | 3 / 3 |

These observations distinguish **tracked-object appearance** from physical
throw identity. The five clear stone crossings are still not independently
verified delivered-stone events. S117's physical identity is unresolved near
the player. The four clear non-stone crossings explain why the original
span/context acceptance rule cannot be applied directly to bridged footage.

The reproducible [crossing-patch diagnostic](scotland24-bridged-development/crossing-patch-diagnostic.json)
scores the nearest same-colour cap/body proposal within 12 px of every one of
the 122 bridged timeline crossings at −0.2, 0, and +0.2 s. It uses the existing
frozen 2022-trained patch model, with no refit. **Nine of ten** bridge review
candidates have at least one positive score; the sole all-negative case is
S156. The model positively scores the S58 jersey logo, S184 player region,
and S191 wheelchair hardware. It also scores 105 of the 112 old timeline
candidates, whose physical correctness is unknown. A one-positive-patch hard
gate would therefore miss three source-visible non-stone failures among these
ten selected cases. This selected set is not a false-positive-rate estimate.

The next verifier must connect cap, granite body, ice contact, movement, and
delivery phase to the **same tracked object**, while abstaining when a player
occludes it. Broad frame motion, split-layout signature, and the current
context patch score do not establish that association. The original 112
candidate timeline and ten new review proposals remain unchanged.

The diagnostic was generated with
[`audit_scotland_crossing_patches.py`](../../../../prototype/scripts/audit_scotland_crossing_patches.py)
and the source crops with
[`render_bridged_crossing_crops.py`](../../../../prototype/scripts/render_bridged_crossing_crops.py).
