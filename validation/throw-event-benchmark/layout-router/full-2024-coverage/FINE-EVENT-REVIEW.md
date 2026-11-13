# Prediction-targeted fine event review

The preceding [two-second sequence review](SEQUENCE-REVIEW.md) left several
same-colour pairs unresolved. This follow-up samples both source views every
0.25 s around Estonia R02-S61/S62 and every 0.5 s around three China events.
The intervals were chosen **after** reading detector output; this is a
development precision diagnostic, not a blind reference or an F1 estimate.
The saved timelines and first scores are unchanged.

| Saved event | Source evidence | Assessment |
| --- | --- | --- |
| Estonia R02-S61, red 6261.075 s | [left](estonia-pair-6261-left-fine/sheet-01.jpg), [right](estonia-pair-6261-right-fine/sheet-02.jpg): a red stone travels through the left view and appears moving down the right view. | Real delivery supported. |
| Estonia R02-S62, red 6280.083 s | [left](estonia-pair-6280-left-fine/sheet-01.jpg), [right](estonia-pair-6280-right-fine/sheet-01.jpg): players and brooms move, while the visible red stone stays at the same right-view position throughout the candidate interval. | Likely false throw event; no new delivered stone visible. The red broom head is a plausible tracked object, but track identity is not proven by these sheets. |
| China R01-S25, red 935.777 s | [left](china24-ratio-935-left-fine/sheet-01.jpg), [right](china24-ratio-935-right-fine/sheet-01.jpg): a red stone travels up the left view and subsequently down the right view. | Real delivery supported despite high lateral-to-longitudinal track velocity ratio. |
| China R01-S173, red 5881.729 s | [left](china24-ratio-5882-left-fine/sheet-01.jpg), [right](china24-ratio-5882-right-fine/sheet-01.jpg): a red broom is swept and raised across the early ice while the right view remains staged for the next throw. | Likely false throw event from broom movement. |
| China R01-S200, red 6494.310 s | [left](china24-ratio-6494-left-fine/sheet-01.jpg), [right](china24-ratio-6494-right-fine/sheet-01.jpg): players and brooms move around the house; no newly travelling red stone is visible. A yellow stone is also present, so colour identity cannot be inferred from proximity alone. | Likely false red throw event; the exact tracked object remains uncertain. |

The four high lateral-to-longitudinal ratio events (absolute `vx/vy` at least
0.60) in the three saved 2024 full timelines are these Estonia and China cases.
Three look false, but China R01-S25 is real. A threshold that simply discards
high-ratio tracks would therefore damage recall. The repeated failure mode is
coloured broom/equipment motion passing the early-ice cap tracker. A viable
confirmation step must establish a stone-shaped moving object and/or matching
motion in the second view while preserving genuine deliveries like R01-S25.

This review was selected from positive predictions. It says nothing about
missed throws elsewhere in these recordings or source coverage gaps.
