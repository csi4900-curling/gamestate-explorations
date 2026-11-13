# Source-specific receiving-house calibration pilot

The [ellipse-affine transfer audit](HOUSE-CALIBRATION-TRANSFER.md) rejected
copying the tuned Korea homography to Latvia or Italy. The next pilot fits a
new image-to-ice-plane transform **at each usable candidate sample**. It uses
the Korea calibration only as an initializer, then fits the target frame's
outer and middle ring paint and the visible transverse hog line at the
nominal 6.401 m from the tee. It holds out one quarter of outer/middle ring
angles and all inner-ring observations from fitting, checks those after fit,
and checks ring and hog-line consistency in the first and last of the three
sampled frames. A failing check returns no transform or projected caps.

| Exposed recording | Stable three-frame ellipse inputs | Conditional image-supported transforms | Cap centers projected as if on ice |
| --- | ---: | ---: | ---: |
| [Canada–Latvia 2024](latvia24-full-v1/right-blind-runner-replay/latvia-source-house-calibration-first.json) | 20 | 5 | 14 |
| [Canada–Italy 2024](new-preflight-italy24/right-blind-runner-replay/italy-source-house-calibration-first.json) | 48 | 11 | 14 |

The remaining inputs abstain because the middle-frame ring/held-out geometry
fails, the optimizer fails, or the transform does not survive the two other
sampled frames. The [reproducible export](../../../../prototype/scripts/export_source_house_calibration.py)
records source, candidate-handoff, ellipse, reference-frame, calibration and
code hashes; it preserves every failed diagnostic. This is a development
probe on exposed recordings, not a held-out calibration benchmark.

**The 28 cap projections are not physical stone coordinates.** A visible cap
is elevated above its contact point on the ice, while the transform assumes
the pixel lies on the ice plane. The image tests do not supply a surveyed
metre-accuracy estimate, stone identity, complete board, or continuous
camera transform. All rows retain `metric_accuracy_validated: false`,
`complete_board_verified: false`, and `simulation_ready: false`.

The [three-frame body-bottom follow-up](../../../../prototype/scripts/export_candidate_contact_projection.py)
applies the existing neutral stone-body cue beneath each accepted cap. It
retains a lower-body pixel only when all three sampled frames return a point
within 2.5 px of their median. The saved [Latvia result](latvia24-full-v1/right-blind-runner-replay/latvia-candidate-contact-projection-first.json)
has 10 such proxies from 14 cap proposals; the [Italy result](new-preflight-italy24/right-blind-runner-replay/italy-candidate-contact-projection-first.json)
has 12 from 14. The median distance **between the cap's plane projection and
the lower-body proxy's plane projection** is 1.437 m in Latvia and 1.511 m in
Italy. That large difference demonstrates why cap centers cannot stand in
for ground contact in this low-angle view. It is **not** a measured correction
error or proof that the lower-body pixel is the actual ice-contact point.

This pilot shows that source-specific projective fitting can recover
internally consistent image geometry for some frames, but its present gates
cover only a minority of partial cap observations. The next required work is
to recover the **stone ground-contact pixel**, estimate/validate transforms
through camera motion, and test positions against independent rink or board
references before using them as game state or simulation inputs.

An additional [strict registered-transfer stage](../../../../prototype/scripts/export_registered_house_calibration.py)
checks whether a failed-fit sample can reuse the nearest accepted transform
from the same routed camera context. It requires a zero-shift painted-house
mask match and ring/hog-line checks in **all three target frames**. The saved
[Latvia ledger](latvia24-full-v1/right-blind-runner-replay/latvia-registered-house-calibration-first.json)
retains five original transforms and adds **one** conditional donor transfer;
the [Italy ledger](new-preflight-italy24/right-blind-runner-replay/italy-registered-house-calibration-first.json)
retains eleven and adds **five**. The other candidate samples abstain, with
their donor and alignment/geometry failures recorded. These transfers are
still image-supported hypotheses, not metric-accuracy validation or proof
that the camera stayed fixed between samples.
