"""Source-pixel ice-context measurement below a 1080p body proposal.

This is the 360p right-track underpoint geometry scaled by three in each
dimension. It is a review cue, not a calibrated ice-plane or stone classifier.
"""

import cv2
import numpy as np


def underpoint_nonice_fraction(frame, pixel, *, min_sample_pixels=2700):
    if frame.shape[:2] != (1080, 1920):
        raise ValueError("Expected 1920x1080 source frame")
    cx, cy = map(round, pixel)
    x0, x1 = max(0, cx - 60), min(1920, cx + 60)
    y0, y1 = max(0, cy + 66), min(1080, cy + 180)
    if (x1 - x0) * (y1 - y0) < min_sample_pixels:
        return None
    hsv = cv2.cvtColor(frame[y0:y1, x0:x1], cv2.COLOR_BGR2HSV)
    ice_like = (hsv[:, :, 1] < 90) & (hsv[:, :, 2] > 150)
    return float((~ice_like).mean())


def review_tier(nonice_fraction, *, clear_max=0.05, clutter_min=0.25):
    if nonice_fraction is None:
        return "context_unavailable"
    if nonice_fraction <= clear_max:
        return "clear_context_review"
    if nonice_fraction > clutter_min:
        return "cluttered_context_review"
    return "ambiguous_context_review"
