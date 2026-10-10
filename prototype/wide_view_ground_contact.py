"""Estimate an ice contact point below a stone cap in low-angle views.

The cap is above the ice. Projecting its pixel through an ice-plane mapping
therefore gives a biased position; the lower edge of the neutral stone body is
a better (still approximate) source-only point for board comparisons.
"""

import cv2
import numpy as np


def contact_below_cap(frame, cap_pixel, *, half_width=10, min_body_pixels=8, max_depth=23):
    """Return the neutral body's bottom midpoint, or ``None`` if unsupported.

    The estimate uses only image colour and the supplied cap location. It does
    not use rink geometry, a diagram, or a chosen board position.
    """
    height, width = frame.shape[:2]
    x, y = (int(round(value)) for value in cap_pixel)
    if x - half_width < 0 or x + half_width >= width or y + max_depth >= height or y + 4 < 0:
        return None
    patch = frame[y + 4 : y + max_depth + 1, x - half_width : x + half_width + 1]
    hsv = cv2.cvtColor(patch, cv2.COLOR_BGR2HSV)
    neutral_body = (hsv[:, :, 1] <= 110) & (hsv[:, :, 2] >= 45) & (hsv[:, :, 2] <= 185)
    support = neutral_body.sum(axis=1)
    rows = np.flatnonzero(support >= min_body_pixels)
    if len(rows) < 4:
        return None
    bottom = int(rows[-1])
    if bottom >= len(support) - 2 or not all(
        support[max(0, bottom - 3) : bottom + 1] >= min_body_pixels
    ):
        return None
    body_columns = np.flatnonzero(neutral_body[bottom])
    if len(body_columns) < min_body_pixels:
        return None
    body_x = x - half_width + (int(body_columns[0]) + int(body_columns[-1])) / 2
    return {
        "pixel": [round(body_x, 2), y + 4 + bottom + 1],
        "supporting_body_rows": int(len(rows)),
        "bottom_row_body_pixels": int(support[bottom]),
    }
