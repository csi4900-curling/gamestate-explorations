# Targeted same-colour sequence review

This is a development audit of the five pairs selected in
[SEQUENCE-REVIEW-PLAN.md](SEQUENCE-REVIEW-PLAN.md). The source-only sheets
sample one full broadcast frame every two seconds. An event's track lasts
less than four seconds, so these sheets alone cannot establish whether a
particular tracked object was a delivered stone, a different moving object,
or the same stone observed twice. No predicted event was accepted, removed,
or recoloured from this review.

| Pair | Source sheet | Frozen event times and direction | Review outcome |
| --- | --- | --- | --- |
| Estonia R01-S12 / S14 | [655–700 s](sequence-review-estonia24-655/sheet-01.jpg) | 667.426 s red, negative y; 678.654 s red, negative y | Unresolved. The sheet shows activity at both ends of the ice, but cannot tie both subsecond tracks to two releases. |
| Estonia R02-S61 / S62 | [6248–6300 s](sequence-review-estonia24-6248/sheet-01.jpg) | 6261.075 s red, negative y; 6280.083 s red, positive y | Unresolved. The opposite motion signs warrant a track-level review; a sign change alone is not a throw identity. |
| China R01-S171 / S173 | [5842–5905 s](sequence-review-china24-5842/sheet-01.jpg) | 5855.833 s red, positive y; 5881.729 s red, positive y | Unresolved. Multiple stones and people are visible; sampling is too sparse to count distinct releases. |
| China R01-S196 / S200 | [6445–6515 s](sequence-review-china24-6445/sheet-01.jpg) | 6459.902 s red, negative y; 6494.310 s red, negative y | Unresolved. The sheet spans active play, but cannot determine whether both detections are deliveries. |
| China R01-S214 / S217 | [7065–7135 s](sequence-review-china24-7065/sheet-01.jpg) | 7080.929 s red, negative y; 7115.583 s red, positive y | Unresolved. Source frames do not prove the identity or colour of either tracked object. |

The audit does identify exact clips for a later frame-rate review. It is not
an independent precision or recall reference: the clips were selected from
the detector's output. High event F1 remains unmeasured on these full
recordings. An exhaustive, held-out event reference must include releases
that the detector did not propose, as well as all proposed events, and must
include the current layout gaps and camera cuts.
