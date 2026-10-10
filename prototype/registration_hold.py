"""Conservative still-camera evidence for borrowing a nearby accepted transform."""

import cv2
import numpy as np


def ice_similarity(frame, anchor, max_gray_difference=4.0,
                   min_phase_response=0.55, max_shift_px=2.5):
    """Compare static lower-ice texture without claiming full metric registration."""
    if frame.shape != anchor.shape:
        raise ValueError("Frame shapes differ")
    def crop(image):
        gray = cv2.cvtColor(image[650:1020, 1010:1880], cv2.COLOR_BGR2GRAY)
        return cv2.GaussianBlur(gray, (5, 5), 0).astype(np.float32)
    current, prior = crop(frame), crop(anchor)
    difference = float(np.mean(np.abs(current - prior)))
    shift, response = cv2.phaseCorrelate(prior, current)
    magnitude = float(np.linalg.norm(shift))
    return {"accepted": bool(difference <= max_gray_difference and
                             response >= min_phase_response and
                             magnitude <= max_shift_px),
            "mean_absolute_grayscale_difference": difference,
            "phase_response": float(response),
            "phase_shift_px": list(map(float, shift)),
            "phase_shift_magnitude_px": magnitude,
            "max_gray_difference": max_gray_difference,
            "min_phase_response": min_phase_response,
            "max_shift_px": max_shift_px}
