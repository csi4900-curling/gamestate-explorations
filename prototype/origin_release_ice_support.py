"""Require broad white ice below a held-cap release cue."""

import cv2
import numpy as np


def below_ice_fraction(frame, held_center_px):
    image = cv2.resize(frame, (640, 360), interpolation=cv2.INTER_AREA)
    x, y = (round(value) for value in held_center_px)
    x0, x1 = max(0, x - 40), min(640, x + 40)
    y0, y1 = max(0, y + 20), min(360, y + 50)
    if x1 - x0 < 60 or y1 - y0 < 15:
        return None
    hsv = cv2.cvtColor(image[y0:y1, x0:x1], cv2.COLOR_BGR2HSV)
    ice = (hsv[:, :, 1] < 75) & (hsv[:, :, 2] > 165)
    return round(float(np.mean(ice)), 4)


def passage_has_ice(frame, passage, *, min_fraction=0.6):
    fraction = below_ice_fraction(frame, passage["held_center_px"])
    return fraction is not None and fraction >= min_fraction, fraction
