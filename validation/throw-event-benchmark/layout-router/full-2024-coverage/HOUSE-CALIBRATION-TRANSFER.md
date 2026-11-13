# Why the tuned house homography does not transfer by ellipse alignment

The [tuned camera calibration](../../../../prototype/rectification/calibration.json)
belongs to a specific Canada–Korea 2024 source frame. The new automated
image-ellipse fit gives a center and vertical scale for the painted receiving
house in Latvia and Italy, but that is not enough to transfer this metric
homography. A second, visually continuous transverse rink marking below the
house supplies a held-out image check.

The [source-hashed audit script](../../../../prototype/scripts/audit_house_affine_transfer.py)
fits the house ellipse in the Korea reference image, locates the strongest
long horizontal edge in a fixed band below it, and transfers that line's
vertical position using only the target ellipse's center and minor-axis
scale. It then measures the line at the middle source frame of each stable
three-frame target ellipse. The line is a visual marking, not a surveyed
ground point; the band and four-pixel rejection threshold were chosen after
inspecting these exposed sources.

| Target recording | Stable house samples | Median observed-minus-transferred line position | 95th percentile absolute residual |
| --- | ---: | ---: | ---: |
| [Canada–Latvia 2024](latvia24-full-v1/right-blind-runner-replay/latvia-house-affine-transfer-audit.json) | 20 | +10.148 px | 12.626 px |
| [Canada–Italy 2024](new-preflight-italy24/right-blind-runner-replay/italy-house-affine-transfer-audit.json) | 48 | +10.463 px | 14.439 px |

Both recordings fail this **simple ellipse-affine transfer** check at 360p.
This does not give a calibrated metric error in metres, and it does not prove
that a separately estimated per-source homography is impossible. It shows
that matching the ring's apparent center and size is insufficient to carry
the tuned calibration to another recording. Accordingly, the current cap
positions remain image-relative; no board or replay output is promoted to
rink metres or simulation-ready state by this fit.

A source-specific planar calibration would need additional correctly
identified rink landmarks spread beyond the house, with held-out landmark
checks and stone-ground-contact handling. Camera changes within a recording
would require repeated calibration or a verified transform between views.
An exploratory [source-specific fit](SOURCE-SPECIFIC-HOUSE-CALIBRATION.md)
now passes image-geometry checks on a minority of frames; its projected cap
centers remain explicitly unvalidated physical positions.
