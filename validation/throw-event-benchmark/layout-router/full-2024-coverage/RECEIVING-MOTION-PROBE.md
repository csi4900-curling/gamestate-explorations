# Second-view motion is useful evidence, but not a throw confirmation by itself

The [fine source review](FINE-EVENT-REVIEW.md) identified likely equipment-led
false events. `prototype/scripts/probe_receiving_view_motion.py` now samples
the right half of the frozen 2024 recordings at 10 Hz for two seconds before
through twelve seconds after selected crossings. It detects coloured cap-like
objects, links nearby observations, and reports every track rather than
selecting a winner. The runner verifies the source video hash against the
saved timeline. Its [Estonia](estonia-receiver-motion-cut-aware.json) and
[China](china-receiver-motion-cut-aware.json) outputs are prediction-targeted
development diagnostics, not event F1 scores.

| Saved event | Largest relevant second-view observation | Interpretation |
| --- | --- | --- |
| Estonia R02-S61, real red throw | Red track from 6266.075–6272.975 s, 70 observations, 134 px displacement. | Strong corresponding moving-stone evidence in the second view. |
| Estonia R02-S62, likely false red event | The earlier red stone remains visible and moves slowly through this later window (140 observations, 31 px displacement); short red equipment tracks also appear. | Same-colour motion alone would misconfirm a **new** throw. Track identity and a new entry are necessary. |
| China R01-S25, real red throw | Red track from 939.277–947.277 s, 78 observations, 219 px displacement. | Strong corresponding moving-stone evidence despite a high first-view lateral-velocity ratio. |
| China R01-S173, likely broom false event | No red track exceeds 11 px displacement during the 14-second probe. | Supports rejection, subject to right-view observability. |
| China R01-S200, likely false red event | Multiple red cap-like tracks exceed 100 px from about 6497 s as players enter the right view. | Raw second-view cap motion is a false corroboration signal. The image-cut test detects no hard edit here; the camera view remains the same. |

The current cap detector accepts some coloured equipment, clothing and wheel
parts. These outputs cannot prove that a moving cap is a stone or that two
camera tracks depict the same physical object. A second-view gate needs
stone-versus-person separation, expected ice trajectory, and a **new**
arrival linked to a first-view passage. A real throw can still be hidden or
cut away, so absent second-view evidence must remain an explicit unknown
rather than an automatic rejection. None of the frozen timelines is altered
by this probe.

A [continuous joint-window probe](estonia-receiver-motion-shared.json) tracks
both Estonia event times together. Its dominant red track spans 6266.075–
6292.075 s with 261 observations and 214 px end-to-end displacement, crossing
the 6280.083 s false candidate without a new red entry or detected hard cut.
This makes an old-stone continuation more plausible than a second throw, while
the greedy track still requires independent identity verification before it
can be used as a general rule.

I also ran the existing [CurlObserver-trained patch model](../../../curlobserver-learned-probe/README.md)
on one right-view frame per reviewed event. The exact model, inference-code
and source hashes, times and boxes are preserved in
`receiver-stone-patch-check.json`. It returned zero right-view boxes at
Estonia 6268 s despite the visible moving red stone; it returned four red
right-view boxes at China 6498 s during the player-heavy false case. These
five prediction-targeted frames are too few for a performance estimate, but
they directly rule out using this overhead-trained model as an unquestioned
confirmation gate for these side views.

I ran the same right-view probe on the 13 real throws previously matched in
the two source-first five-minute windows: [six Estonia events](estonia-receiver-motion-window2.json)
and [seven China events](china-receiver-motion-window2.json). Even within this
favourable development set, a same-colour track with at least seven
observations and 30 px displacement appears for only 6/13 real throws
(Estonia 5/6; China 1/7). The same rule appears for 2/3 likely false events
above (Estonia R02-S62 and China R01-S200). Relaxing it to six observations
and 20 px finds 11/13 real throws but still finds those same 2/3 likely false
events. These thresholds are diagnostic examples, not fitted detector
parameters or an independent estimate of precision and recall. The poor
separation means this cap-track feature cannot be promoted as a hard
confirmation or rejection rule. The China misses particularly show that
right-view cap visibility varies across otherwise real first-view passages.
