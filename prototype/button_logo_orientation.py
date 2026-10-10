"""Source-only orientation cue from the asymmetric rink-button emblem.

This cue applies to the Beijing 2022 Paralympic house logo. It abstains when
the inner button is occluded or its colour ordering is too weak to resolve.
"""

import cv2
import numpy as np


def logo_colour_signature(frame, center_px, outer_axes_px, *, inner_ratio=8,
                          min_red_pixels=8, min_blue_pixels=20,
                          min_axis_separation_px=3):
    """Return red/blue ordering inside the painted button, or ``None``.

    ``outer_axes_px`` are the house's horizontal and vertical *radii* in the
    same 640×360 image. The central elliptical ROI excludes the red house
    ring, so it uses the asymmetric emblem rather than stone locations.
    """
    if frame is None or frame.ndim != 3 or frame.shape[2] != 3:
        raise ValueError("Expected BGR frame")
    if frame.shape[:2] != (360, 640):
        raise ValueError("Expected 640×360 source frame")
    cx, cy = center_px
    rx, ry = outer_axes_px
    if rx <= 0 or ry <= 0 or inner_ratio <= 0:
        raise ValueError("House axes and ROI ratio must be positive")
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    hue, saturation, value = cv2.split(hsv)
    ys, xs = np.ogrid[:360, :640]
    inner = (((xs - cx) / (rx / inner_ratio)) ** 2
             + ((ys - cy) / (ry / inner_ratio)) ** 2) < 1
    red = (inner & (((hue < 10) | (hue > 170))
                    & (saturation > 55) & (value > 60)))
    blue = (inner & (hue > 95) & (hue < 135)
            & (saturation > 45) & (value > 60))
    red_y, red_x = np.where(red)
    blue_y, blue_x = np.where(blue)
    if len(red_x) < min_red_pixels or len(blue_x) < min_blue_pixels:
        return None
    red_lateral_px = float(red_x.mean() - cx)
    red_minus_blue_vertical_px = float(red_y.mean() - blue_y.mean())
    if (abs(red_lateral_px) < min_axis_separation_px or
            abs(red_minus_blue_vertical_px) < min_axis_separation_px):
        return None
    return {
        "red_lateral_sign": 1 if red_lateral_px > 0 else -1,
        "red_minus_blue_vertical_sign": 1 if red_minus_blue_vertical_px > 0 else -1,
        "red_lateral_px": round(red_lateral_px, 2),
        "red_minus_blue_vertical_px": round(red_minus_blue_vertical_px, 2),
        "red_pixel_count": len(red_x),
        "blue_pixel_count": len(blue_x),
        "source_cue": "painted_paralympic_button_red_blue_ordering",
    }


def relative_view_rotation(first, second):
    """Return 0 or 180 degrees when both logo axes agree; otherwise abstain."""
    if first is None or second is None:
        return None
    lateral = first["red_lateral_sign"] * second["red_lateral_sign"]
    vertical = (first["red_minus_blue_vertical_sign"]
                * second["red_minus_blue_vertical_sign"])
    if lateral == vertical == 1:
        return 0
    if lateral == vertical == -1:
        return 180
    return None
