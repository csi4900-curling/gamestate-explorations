"""Require repeated neutral-body bottom pixels before conditional plane projection."""

from math import dist
from statistics import median


def stable_body_bottom(contacts, *, max_spread_px=2.5):
    if len(contacts) != 3 or any(item is None for item in contacts):
        return None, "abstain_missing_body_bottom_in_three_frames"
    pixels = [item["pixel"] for item in contacts]
    center = [median(item[axis] for item in pixels) for axis in (0, 1)]
    spread = max(dist(point, center) for point in pixels)
    if spread > max_spread_px:
        return None, "abstain_unstable_body_bottom"
    return {"body_bottom_pixel_median": [round(value, 2) for value in center],
            "max_body_bottom_spread_px": round(spread, 3),
            "supporting_frame_count": 3,
            "body_bottom_proxy_not_verified_ice_contact": True}, \
        "conditional_repeated_body_bottom_proxy"
