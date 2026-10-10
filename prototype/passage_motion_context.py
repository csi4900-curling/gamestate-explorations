"""Source-frame motion measurements around a candidate passage point."""

import cv2
import numpy as np


def motion_context_features(before, after, *, x, y):
    """Measure changed image area near a tracked cap without deciding identity."""
    a = cv2.cvtColor(cv2.resize(before, (640, 360)), cv2.COLOR_BGR2GRAY)
    b = cv2.cvtColor(cv2.resize(after, (640, 360)), cv2.COLOR_BGR2GRAY)
    changed = cv2.absdiff(a, b) >= 24
    x, y = round(x), round(y)

    def count(half_width, half_height):
        x0, x1 = max(0, x - half_width), min(640, x + half_width + 1)
        y0, y1 = max(0, y - half_height), min(360, y + half_height + 1)
        return int(np.count_nonzero(changed[y0:y1, x0:x1]))

    return {
        "changed_px_32x32": count(16, 16),
        "changed_px_80x80": count(40, 40),
        "changed_px_100x120": count(50, 60),
    }
