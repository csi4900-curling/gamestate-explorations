"""Transport an accepted calibration to a recording-local camera reference."""

from copy import copy

import cv2


def rebase_view_calibrator(base_calibrator, anchor_frame, *, max_corner_displacement_px):
    """Rebase only when the original reference registers at the anchor frame.

    The transported metric map inherits the old calibration's uncertainty.
    This changes feature matching, not measured rink geometry.
    """
    H, registration = base_calibrator.register(
        anchor_frame, max_corner_displacement_px=max_corner_displacement_px
    )
    if H is None:
        raise ValueError(f"Anchor registration rejected: {registration.get('reason')}")
    local = copy(base_calibrator)
    local.reference = anchor_frame.copy()
    local.H = H.copy()
    local.kp, local.desc = local.sift.detectAndCompute(
        cv2.cvtColor(local.reference, cv2.COLOR_BGR2GRAY), local.mask
    )
    if local.desc is None or len(local.kp) < 12:
        raise ValueError("Anchor has too few local reference features")
    return local, registration
