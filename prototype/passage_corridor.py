"""Camera-calibrated ice-corridor evidence for provisional passage events.

This screen is source/layout dependent. It does not assert that off-corridor
observations are impossible throws; it retains them as withheld candidates.
"""

import math


def screen_corridor(events, *, center_x_px, half_width_px):
    if not all(math.isfinite(x) for x in (center_x_px, half_width_px)):
        raise ValueError("Corridor geometry must be finite")
    if half_width_px <= 0:
        raise ValueError("Corridor half width must be positive")
    ids = [e["id"] for e in events]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate event IDs")
    screened = []
    for event in events:
        x = event["crossing_x_px"]
        if not isinstance(x, (int, float)) or isinstance(x, bool) or not math.isfinite(x):
            raise ValueError(f"Invalid crossing x for {event['id']}")
        inside = abs(x - center_x_px) <= half_width_px
        screened.append(
            {
                "id": event["id"],
                "crossing_time_s": event["crossing_time_s"],
                "colour": event["colour"],
                "crossing_x_px": x,
                "status": "ice_corridor_candidate" if inside else "off_corridor_unconfirmed",
            }
        )
    return screened
