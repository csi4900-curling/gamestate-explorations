"""Camera-relative location of cap proposals around a painted house ellipse."""

from math import hypot, isfinite


def normalized_house_distance(ellipse, pixel):
    """Return image-ellipse radii; this is not a metric ice coordinate."""
    if ellipse is None:
        return None
    angle = float(ellipse["angle_degrees_opencv"])
    if not isfinite(angle) or abs(angle - 90) > 10:
        raise ValueError("Unsupported rotated frontal house ellipse")
    cx, cy = (float(value) for value in ellipse["center_px"])
    major, minor = (float(value) for value in ellipse["axis_lengths_px"])
    x, y = (float(value) for value in pixel)
    if (not all(isfinite(value) for value in (cx, cy, major, minor, x, y))
            or major <= 0 or minor <= 0):
        raise ValueError("Invalid house ellipse or cap point")
    return hypot((x - cx) / (major / 2), (y - cy) / (minor / 2))


def house_location_tier(distance, *, near_distance=1.4):
    if distance is None:
        return "house_geometry_unavailable_review"
    if not isfinite(distance) or not isfinite(near_distance) or near_distance <= 0:
        raise ValueError("Invalid house distance")
    return ("near_painted_house_review" if distance <= near_distance
            else "outside_painted_house_review")
