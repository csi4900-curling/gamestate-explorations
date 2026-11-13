# Latvia-developed 1080p underpoint cue on Czech reviewed prefixes

The [transfer artifact](full-source-reviewed-highres-underpoint-latvia-rule-transfer-development.json)
applies the unchanged [Latvia 1080p underpoint measurement](../../../prototype/highres_underpoint_context.py)
and its 0.05/0.25 **review tiers** to selected Czech 2024 source-reviewed
prefixes. The prior [Latvia development artifact](../canada-latvia-2024/end6-highres-underpoint-context-development.json)
pins the feature code hash. The Czech runner verifies the full 1920×1080
video hash, the existing zero-offset 360p↔1080p alignment, the 360p proposal
score artifact, both source-review artifacts and every selected sample time.
It scales each 360p cap-box center by three before sampling the full-resolution
video. It does not refit a threshold using Czech source labels.

| Same-agent marked source-pixel class | Clear | Ambiguous | Cluttered |
| --- | ---: | ---: | ---: |
| Moving-stone pixels | 20 | 0 | 0 |
| Person/equipment pixels | 0 | 0 | 23 |

All 20 stone-prefix median non-ice fractions are 0.0000. The 23
person/equipment medians range from 0.2958 to 1.0000. Forty-two paths
have three available source samples; one has two. This selected-source
result supports using the cue to **prioritize review** across two recordings;
it is not an object-detector precision/recall estimate or a physical throw
F1 score. The source classes were assigned by the detector developer after
viewing candidate pixels, and the positive and right-only negative groups
were selected by earlier pipeline outputs.

The Czech centers are scaled **cap** boxes, while the Latvia pilot sampled
high-resolution **body** template centers, typically lower in the image.
The same geometric band therefore covers related but not identical patches.
The broader Latvia evidence also supplies counterexamples to a hard context
gate: one clearly person/equipment prefix, R0117, had a previously clear
paired-context score with 0.2454 underpoint non-ice fraction; under the
current three-way interpretation that value would be *ambiguous*. A visibly
moving stone prefix, R01:A444, was cluttered by the earlier ring-plus-band
rule because nearby foreground crossed the ring. The new underpoint-only
cue does not establish that every clear path is a stone or every cluttered
path is false. White clothing, painted ice, occlusion, and view changes remain
untested or ambiguous.

Reproduce with `feasibility/scripts/python.sh
prototype/scripts/transfer_czech_highres_underpoint.py` after preserving
the existing output. The result contains every sampled frame index, scaled
center, fraction and source-review class for audit.
