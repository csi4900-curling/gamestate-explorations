# How accurate is the left-camera projection away from the house?

The viewer's `y ≥ −6.401 m` cutoff is a **software scope limit**, not a measured
failure point. Its original homography is fitted to four outer-house-ring
intersections; its nine held-out points are also on the house. That alone cannot
measure stone-position accuracy farther along the ice.

We checked a separate, known marking: the hog line. [World Curling's rules](../../feasibility/sources/Rules-2025.pdf)
(PDF page 4) place its inside edge 6.401 m from the tee centre and give it a
102 mm width. On the far side of this house, the painted line centre should
therefore be at **y = −6.452 m**. This marking was not used to fit either house
homography. A colour-based measurement samples the purple stripe in nine
columns of the clear reference frame and eight unoccluded columns at T11 clip
time 43.5 s. The resulting median absolute deviations from nominal line
centre are:

| Homography | Clear reference | T11 frame |
| --- | ---: | ---: |
| Original house calibration used by the continuous viewer | 1.41 cm | **0.65 cm** |
| Later ring-refined calibration | 6.90 cm | 7.55 cm |

These are **paint-alignment checks at the hog line**, not measured physical
stone-position errors. The actual rink dimensions, stripe centre detection,
camera registration and lens model all add uncertainty. The check does show
that the original homography is not simply failing as it approaches the
configured boundary.

For the yellow T11 stone, separately observed cap-centre pixels at source
2303.5, 2304.5 and 2305.0 s project with the refined house homography to
approximately **−9.12, −11.40 and −12.57 m**. The original and refined
homographies disagree there by **12.5, 17.5 and 20.4 cm** in the longitudinal
coordinate. The project's conditional cap-height correction shifts those
three projected positions **63.2–70.6 cm** toward the house. Neither the model
disagreement nor the conditional height adjustment is an absolute error bound.

There is no independently located longitudinal marking or surveyed stone
ground point at those distant positions in this view. We therefore **cannot
measure the actual physical-coordinate error at −9 to −13 m from these data**.
The current exclusion is conservative presentation policy. Extending the board
for exploratory trajectories is reasonable if positions are labelled
provisional; claiming coaching-grade accuracy needs distant surveyed markings
or independently measured stone positions.

Reproduce the measurements with
`feasibility/scripts/python.sh prototype/scripts/audit_far_homography.py`.
The per-column and per-stone values are in
[far-homography-audit.json](far-homography-audit.json).
