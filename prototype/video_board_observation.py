"""Detect a clear broadcast overhead house and visible coloured stones."""

import cv2
import numpy as np


def blue_ring_mask(frame):
    if frame.shape != (360, 640, 3):
        raise ValueError("Expected 640×360 BGR broadcast frame")
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    return (
        (hsv[:, :, 0] >= 96) & (hsv[:, :, 0] <= 115) & (hsv[:, :, 1] > 140) & (hsv[:, :, 2] > 170)
    )


def annulus_support(mask, cx, cy, radius):
    rows = []
    for theta in np.linspace(0, 2 * np.pi, 72, endpoint=False):
        rr = np.linspace(0.65 * radius, 1.02 * radius, 10)
        xx = np.rint(cx + rr * np.cos(theta)).astype(int)
        yy = np.rint(cy + rr * np.sin(theta)).astype(int)
        valid = (xx >= 0) & (xx < mask.shape[1]) & (yy >= 0) & (yy < mask.shape[0])
        if valid.any():
            rows.append(float(np.mean(mask[yy[valid], xx[valid]])))
    return {
        "mean_blue_fraction": round(float(np.mean(rows)), 3) if rows else 0,
        "supported_angle_bins": sum(value > 0.4 for value in rows),
        "visible_angle_bins": len(rows),
    }


def detect_overhead_house(frame, *, min_mean_blue_fraction=0.4, min_supported_angle_bins=30):
    mask = blue_ring_mask(frame)
    circles = cv2.HoughCircles(
        (mask.astype(np.uint8) * 255),
        cv2.HOUGH_GRADIENT,
        dp=1.5,
        minDist=120,
        param1=100,
        param2=25,
        minRadius=65,
        maxRadius=180,
    )
    options = []
    if circles is not None:
        for x, y, r in circles[0]:
            cx, cy, radius = round(float(x)), round(float(y)), round(float(r))
            # A full overhead sheet places the house near the horizontal centre.
            # Side-wall graphics can otherwise imitate a blue annulus.
            if not 180 <= cx <= 460:
                continue
            support = annulus_support(mask, cx, cy, radius)
            if (
                support["mean_blue_fraction"] >= min_mean_blue_fraction
                and support["supported_angle_bins"] >= min_supported_angle_bins
            ):
                options.append(
                    {"center_px": [cx, cy], "outer_radius_px": radius, "annulus_support": support}
                )
    if not options:
        return None
    options.sort(
        key=lambda row: (
            -row["annulus_support"]["mean_blue_fraction"],
            -row["annulus_support"]["supported_angle_bins"],
            abs(row["center_px"][0] - 320),
        )
    )
    house = options[0]
    cy = house["center_px"][1]
    house["delivery_side"] = "top" if cy > 200 else "bottom" if cy < 160 else "uncertain"
    return house


def detect_board_stones(frame, house, *, min_cap_pixels=30):
    if house is None:
        raise ValueError("Accepted overhead house required")
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    circles = cv2.HoughCircles(
        gray, cv2.HOUGH_GRADIENT, dp=1, minDist=12, param1=80, param2=15, minRadius=5, maxRadius=12
    )
    if circles is None:
        return []
    cx, cy = house["center_px"]
    radius = house["outer_radius_px"]
    stones = []
    for x_raw, y_raw, r_raw in circles[0]:
        x, y = round(float(x_raw)), round(float(y_raw))
        if not (abs(x - cx) <= 1.65 * radius and abs(y - cy) <= 3 * radius):
            continue
        x0, x1 = max(0, x - 5), min(640, x + 6)
        y0, y1 = max(0, y - 5), min(360, y + 6)
        patch = hsv[y0:y1, x0:x1]
        yy, xx = np.mgrid[y0:y1, x0:x1]
        disc = (xx - x) ** 2 + (yy - y) ** 2 < 25
        red = (
            ((patch[:, :, 0] < 12) | (patch[:, :, 0] > 170))
            & (patch[:, :, 1] > 90)
            & (patch[:, :, 2] > 60)
            & disc
        )
        yellow = (
            (patch[:, :, 0] > 16)
            & (patch[:, :, 0] < 43)
            & (patch[:, :, 1] > 90)
            & (patch[:, :, 2] > 70)
            & disc
        )
        counts = {"red": int(np.count_nonzero(red)), "yellow": int(np.count_nonzero(yellow))}
        colour = max(counts, key=counts.get)
        if counts[colour] < min_cap_pixels:
            continue
        stone = {
            "colour": colour,
            "pixel": [x, y],
            "cap_colour_pixels": counts[colour],
            "hough_radius_px": round(float(r_raw), 2),
        }
        if house["delivery_side"] != "uncertain":
            sign = 1 if house["delivery_side"] == "top" else -1
            stone["canonical_lateral_house_radii"] = round(sign * (x - cx) / radius, 4)
            stone["longitudinal_house_radii"] = round(sign * (y - cy) / radius, 4)
        stones.append(stone)
    return sorted(stones, key=lambda row: (row["colour"], row["pixel"][1], row["pixel"][0]))
