"""Cluster source-video stones within one camera shot in image-house coordinates."""

from bisect import bisect_right
from collections import defaultdict

from prototype.temporal_board_state import stable_board_stones


def stable_image_boards_by_camera_shot(observations, camera_shots):
    """Do not merge positions across a camera cut or assume delivery direction."""
    starts = [row["interval_s"][0] for row in camera_shots]
    if any(a >= b for a, b in zip(starts, starts[1:])):
        raise ValueError("Camera shots must have increasing starts")
    grouped = defaultdict(list)
    for row in observations:
        t = row["time_s"]
        index = bisect_right(starts, t) - 1
        if index < 0 or t >= camera_shots[index]["interval_s"][1]:
            raise ValueError(f"Observation outside camera-shot intervals: {t}")
        house = row["house"]
        cx, cy = house["center_px"]
        radius = house["outer_radius_px"]
        if radius <= 0:
            raise ValueError("Invalid house radius")
        stones = [{"colour": stone["colour"],
                   "canonical_lateral_house_radii": (stone["pixel"][0] - cx) / radius,
                   "longitudinal_house_radii": (stone["pixel"][1] - cy) / radius}
                  for stone in row["stones"]]
        grouped[camera_shots[index]["id"]].append({"time_s": t, "stones": stones,
                                                    "detected_delivery_side": house["delivery_side"]})
    result = []
    for shot in camera_shots:
        frames = grouped.get(shot["id"])
        if not frames:
            continue
        stable = stable_board_stones(frames)
        stones = [{"colour": stone["colour"],
                   "image_house_radius_coordinates": [stone["canonical_lateral_house_radii"],
                                                      stone["longitudinal_house_radii"]],
                   "supporting_frame_count": stone["supporting_frame_count"],
                   "first_seen_s": stone["first_seen_s"],
                   "last_seen_s": stone["last_seen_s"],
                   "max_position_spread_house_radii": stone["max_position_spread_house_radii"]}
                  for stone in stable]
        sides = sorted({frame["detected_delivery_side"] for frame in frames
                        if frame["detected_delivery_side"] != "uncertain"})
        result.append({"camera_shot_id": shot["id"],
                       "accepted_frame_count": len(frames),
                       "observation_interval_s": [frames[0]["time_s"], frames[-1]["time_s"]],
                       "detected_delivery_side": sides[0] if len(sides) == 1 else None,
                       "stable_image_relative_stones": stones,
                       "coordinate_semantics": "Image house radii: +x right, +y down; no physical direction inferred."})
    return result
