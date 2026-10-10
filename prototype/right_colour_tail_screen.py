"""One-frame same-colour continuation screen with explicit abstention."""

from math import hypot

import cv2


AREA_MIN, AREA_MAX = 200, 3500
MAX_CENTER_DISTANCE_PX = 30


def screen_next_colour_frame(frame, colour, predicted_cap_center_1080p_px):
    if frame.shape[:2] != (1080, 1920):
        raise ValueError("Expected a native 1080p source frame")
    px, py = predicted_cap_center_1080p_px
    x1, x2 = max(960, int(px - 100)), min(1920, int(px + 100))
    y1, y2 = max(0, int(py - 90)), min(1080, int(py + 90))
    if x1 >= x2 or y1 >= y2:
        return {"status": "predicted_region_outside_frame",
                "candidates": []}
    hsv = cv2.cvtColor(frame[y1:y2, x1:x2], cv2.COLOR_BGR2HSV)
    if colour == "yellow":
        mask = cv2.inRange(hsv, (17, 71, 66), (42, 255, 255))
    elif colour == "red":
        mask = (cv2.inRange(hsv, (0, 71, 46), (11, 255, 255)) |
                cv2.inRange(hsv, (171, 71, 46), (179, 255, 255)))
    else:
        raise ValueError("Unsupported colour")
    count, _, stats, centers = cv2.connectedComponentsWithStats(mask)
    candidates = []
    for i in range(1, count):
        x, y, width, height, area = (int(value) for value in stats[i])
        cx, cy = float(centers[i, 0] + x1), float(centers[i, 1] + y1)
        distance = hypot(cx - px, cy - py)
        if (AREA_MIN <= area <= AREA_MAX and width >= 7 and height >= 4
                and distance <= MAX_CENTER_DISTANCE_PX):
            candidates.append({
                "center_1080p_px": [round(cx, 2), round(cy, 2)],
                "colour_area_px2": area,
                "prediction_distance_px": round(distance, 2),
                "touches_frame_bottom": y1 + y + height >= 1080,
            })
    candidates.sort(key=lambda item: (item["prediction_distance_px"],
                                      -item["colour_area_px2"]))
    return {"status": ("unique_colour_component_provisional" if
                       len(candidates) == 1 else "abstain_ambiguous_or_absent"),
            "candidates": candidates}


def predict_next_cap_center(points):
    if len(points) < 2:
        raise ValueError("At least two cap points required")
    prior, last = points[-2:]
    dt = last["time_s"] - prior["time_s"]
    if dt <= 0 or dt > 2:
        raise ValueError("Cap tail is not consecutively sampled")
    return [3 * (last["pixel"][axis] +
                 (last["pixel"][axis] - prior["pixel"][axis]) / dt)
            for axis in (0, 1)]
