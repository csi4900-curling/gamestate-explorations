"""Conservative local yellow-handle crop centering around a provisional track."""

import cv2
import numpy as np


def locate_yellow_handle(frame, x, y):
    """Return one yellow component near (x,y), or abstain if ambiguous.

    Coordinates refer to the original 1920x1080-like frame. This is only a
    local handle observation, not a physical stone identity decision.
    """
    x, y = int(round(x)), int(round(y))
    roi = frame[y - 40 : y + 8, x - 80 : x + 80]
    if roi.shape[:2] != (48, 160):
        return {"status": "crop_out_of_frame", "center_pixel": None, "plausible_component_count": 0}
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    mask = (
        (hsv[:, :, 0] > 16) & (hsv[:, :, 0] < 42) & (hsv[:, :, 1] > 65) & (hsv[:, :, 2] > 75)
    ).astype(np.uint8)
    count, _, stats, _ = cv2.connectedComponentsWithStats(mask)
    components = []
    for component in range(1, count):
        left, top, width, height, area = (int(v) for v in stats[component])
        center_offset = left + width / 2 - 80
        if area >= 100 and 8 <= width <= 100 and 5 <= height <= 46 and abs(center_offset) < 70:
            components.append(
                {
                    "center_offset_px": center_offset,
                    "area_px2": area,
                    "bounds_in_roi": [left, top, width, height],
                }
            )
    if len(components) != 1:
        return {
            "status": "no_unique_yellow_component"
            if not components
            else "ambiguous_multiple_yellow_components",
            "center_pixel": None,
            "plausible_component_count": len(components),
        }
    component = components[0]
    return {
        "status": "unique_local_yellow_component",
        "center_pixel": [int(round(x + component["center_offset_px"])), y],
        "plausible_component_count": 1,
        "center_offset_px": round(component["center_offset_px"], 2),
        "component_area_px2": component["area_px2"],
        "component_bounds_in_roi": component["bounds_in_roi"],
    }
