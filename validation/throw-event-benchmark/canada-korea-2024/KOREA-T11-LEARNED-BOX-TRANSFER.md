# Existing learned stone models on Canada–Korea T11

Two frozen stone-box models were run at 1 Hz over the full 90-second Canada–Korea
1080p clip: the [original public-box model](../../curlobserver-learned-probe/model-v2/model.npz)
and the [public-tracking model](../../curlobserver-learned-probe/public-tracking-v2/model.npz).
Their full-interval outputs are [204 boxes](t11-model-v2-boxes-development.json)
and [199 boxes](t11-public-tracking-boxes-development.json), respectively.
These are image detections, not throw-event predictions or false-positive counts.

The [stage audit](t11-learned-box-stage-audit-development.json) tests why
neither model follows the source-visible T11 yellow stone. It uses the
previously source-reviewed T11 template locations at 2308–2314 s, then a
provisional cap track with an explicitly postreview 15 px body offset at
2315–2319 s. A generous 40 px centre radius in the original 1080p image
defines a *nearby* box for this diagnostic; it is not an independent label or
an IoU-based object score.

| Stage across 12 one-second T11 samples | Original model | Public-tracking model |
| --- | ---: | ---: |
| Frame with a nearby raw yellow colour proposal | 12 | 12 |
| Frame with a nearby raw proposal above classifier threshold | 0 | 0 |
| Frame with an accepted nearby yellow box | 0 | 0 |

The best nearby score of the public-tracking model is **1.29**, just below its
frozen **1.34** threshold, at 2314 s; its other eleven best scores range from
about −0.33 to 0.99. The original model's best nearby score is **−0.16**
against its **2.66** threshold. The candidate generator does cover the
moving stone in this sample, but the learned appearance screen rejects it.
Merely lowering either threshold based on these reviewed frames would be
postreview tuning, with unknown false-positive cost elsewhere.

A separate [side-view cap-context verifier](t11-sideview-cap-patch-development.json),
trained on selected Canada–China crops and previously frozen at a zero score
threshold, accepts a nearby raw yellow proposal in **7 of these 12** T11
frames: 2308 and 2314–2319 s. It rejects the five intervening frames.
The earlier low-score body template follows T11 at 2308–2314 s, so the two
*review-position-selected* cues cover different portions of this example.
This is evidence that their appearance signals are complementary; it is not
an operational fused track. A runtime method must select the correct proposal
without knowing T11's location, bridge gaps, and reject unrelated yellow
objects across the full clip.

A subsequent [full-clip template-to-cap handoff](KOREA-T11-UNPOSITIONED-HANDOFF.md)
does select a continuous T11 image path without being given reviewed T11
positions. It remains postreview development on this match, with unverified
physical identity and no independent event F1.

The template and learned-model failures therefore occur at different parts
of the observation pipeline: the fixed 1080p body template loses appearance
score as scale and surroundings change, while the 360p learned classifier
rejects nearby colour proposals throughout T11. A view- and scale-diverse
stone appearance model is the next component to test, followed by temporal
identity and camera handoff. None of these selected-frame results measures
full-match throw precision, recall, cross-view identity, or physical stop.

Reproduce the full scans with `prototype/scripts/probe_stone_patch_video.py`
using each frozen model, `--video prototype/continuous/clip.mp4 --start 0
--end 90`, then run
`feasibility/scripts/python.sh prototype/scripts/audit_korea_t11_learned_boxes.py`
and `feasibility/scripts/python.sh prototype/scripts/audit_korea_t11_sideview_patch.py`.
The JSON artifacts pin source, model, code and runner hashes.
