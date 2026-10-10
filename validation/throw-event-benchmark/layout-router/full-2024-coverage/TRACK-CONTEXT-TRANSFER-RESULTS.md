# Same-track surrounding-motion cue: Scotland development and Latvia transfer

The [pre-Latvia plan](TRACK-CONTEXT-TRANSFER-PLAN.md) froze a three-way
development cue after source inspection of the Scotland bridge candidates.
The unchanged 2024 detector was replayed over Scotland 90–7200 s and Latvia
90–6930 s. Its [Scotland track sidecar](scotland24-bridged-development/raw-track-points.json)
exactly reproduces **194/194** frozen raw events and 71,100 sampled frames;
the [Latvia sidecar](latvia24-full-v1/raw-track-points.json) exactly reproduces
**119/119** raw events and 68,400 samples. Each records the source-hashed
per-frame cap/body observations for the event's image track. An image track
can still switch physical objects or follow a jersey, broom or wheelchair.

The [surrounding-motion probe](../../../../prototype/scripts/audit_track_surrounding_motion.py)
compares an annulus 12–30 px around the tracked cap in two source frames:
does the image match better at its original location or after translating
with the candidate track? Negative index favours a stationary ice/background
context; positive favours surroundings that move with the candidate. The
frozen [three-way cue](../../../../prototype/track_context_triage.py) marks
index ≤ −0.20 `isolated_motion_cue`, ≥ +0.20
`comoving_context_review`, and intermediate/undefined cases ambiguous or
abstained. **No status changes event acceptance.**

| Source and existing gate | Isolated | Ambiguous | Comoving | No score | Total |
| --- | ---: | ---: | ---: | ---: | ---: |
| Scotland bridged run, previously accepted | 74 | 42 | 6 | 0 | 122 |
| Scotland bridged run, previously withheld | 6 | 31 | 34 | 1 | 72 |
| Latvia original run, previously accepted | 53 | 17 | 2 | 0 | 72 |
| Latvia original run, previously withheld | 2 | 17 | 28 | 0 | 47 |

The [Scotland cue ledger](scotland24-bridged-development/context-review-triage.json)
and [Latvia cue ledger](latvia24-full-v1/context-review-triage.json) retain
every raw candidate and its previous gate result. The concentration of
comoving cues among withheld proposals shows the measurement is sensitive to
one nuisance mechanism. It does **not** validate a veto or prove that the
isolated candidates are deliveries.

The [five highest-index previously accepted Latvia cases](latvia24-full-v1/highest-comovement-accepted-review-selection.json)
were selected by the fixed rank before opening their
[source crossing crops](latvia24-full-v1/highest-comovement-crossing-crops/manifest.json).
S45 tracks a moving player at 1882.30 s. **S96, S35, S38 and S87 show
stone bodies at their tracked crossings**, despite high comovement indices
(+0.208, +0.177, +0.176 and +0.132). Thus even the two candidates above the
+0.20 review threshold split between player and stone. A hard comovement veto
would wrongly discard source-visible stone observations. These stone
crossings have not been independently verified as delivered-stone events.

Conversely, the two [isolated-cue Latvia proposals withheld by the existing
filter](latvia24-full-v1/isolated-withheld-review-selection.json) are **not**
rescues. Their [crossing crops](latvia24-full-v1/isolated-withheld-crossing-crops/manifest.json)
show S10 following a Canadian player's head and S72 following a person
bending over the ice. S10 was withheld for leaving the image corridor;
S72 for excessive surrounding motion. The source sheets are
prediction-targeted development review, not independent negative labels.

The Scotland [full-candidate context measurements](scotland24-bridged-development/surrounding-motion-diagnostic.json)
and [Latvia transfer measurements](latvia24-full-v1/surrounding-motion-diagnostic.json)
therefore supply a reproducible **review-priority feature**, but no safe
physical-stone verifier. A robust next stage must check object silhouette,
granite body and ice contact across the track, separate it from nearby people
or equipment, and connect it to a delivery episode. Camera pose and occlusion
must permit an explicit unknown state. High precision/recall still require an
independent complete-match timestamped reference.

Reproduce the exact track sidecars with
[`capture_span_track_points.py`](../../../../prototype/scripts/capture_span_track_points.py),
the three-way ledgers with
[`apply_track_context_triage.py`](../../../../prototype/scripts/apply_track_context_triage.py),
and the fixed source selection/crops with
[`select_context_review_cases.py`](../../../../prototype/scripts/select_context_review_cases.py)
and [`render_context_selection_crops.py`](../../../../prototype/scripts/render_context_selection_crops.py).
