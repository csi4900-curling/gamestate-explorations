"""Conservative complete-house gate for 2022 overhead board observations.

V1 remains frozen for the first transfer audit. This version derives the blue
ring from a connected component, so one-frame Hough instability does not lose
a clear house, and requires most of the ring to be visible.
"""

import cv2
import numpy as np

from prototype.video_board_observation import (
    annulus_support,
    blue_ring_mask,
    detect_board_stones as detect_board_stones,  # re-exported
)


def detect_overhead_house(frame, *, min_supported_angle_bins=60):
    mask = blue_ring_mask(frame)
    count, _, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8))
    options = []
    for index in range(1, count):
        x, y, width, height, area = (int(value) for value in stats[index])
        if not (140 <= width <= 360 and 140 <= height <= 360):
            continue
        if not 0.85 <= width / height <= 1.15:
            continue
        cx, cy = round(x + width / 2), round(y + height / 2)
        if not 180 <= cx <= 460:
            continue
        radius = round((width + height) / 4)
        # Broad coloured graphics have no empty house centre. This also
        # rejects thin fragments whose component area is unlike an annulus.
        fill_fraction = area / (width * height)
        if not 0.23 <= fill_fraction <= 0.62:
            continue
        support = annulus_support(mask, cx, cy, radius)
        if support["supported_angle_bins"] < min_supported_angle_bins:
            continue
        options.append(
            {
                "center_px": [cx, cy],
                "outer_radius_px": radius,
                "annulus_support": support,
                "component_fill_fraction": round(fill_fraction, 3),
                "component_bbox_px": [x, y, width, height],
            }
        )
    if not options:
        return None
    options.sort(
        key=lambda row: (
            -row["annulus_support"]["supported_angle_bins"],
            -row["annulus_support"]["mean_blue_fraction"],
            abs(row["center_px"][0] - 320),
        )
    )
    house = options[0]
    cy = house["center_px"][1]
    house["delivery_side"] = "top" if cy > 200 else "bottom" if cy < 160 else "uncertain"
    return house
