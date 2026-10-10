"""Flag possible window-truncated copies of a motion track for source review."""

from math import dist


def find_near_duplicate_pairs(episodes):
    """Conservative geometry audit, not a proof of physical stone identity.

    Candidate windows can truncate the same 1 Hz local track differently.
    Compare only records with identical colour and near-identical endpoints,
    span, and onset; never infer equivalence from temporal overlap alone.
    """
    ordered = sorted(episodes, key=lambda row: row["motion_interval_s"][0])
    pairs = []
    for i, left in enumerate(ordered):
        left_start, left_end = left["motion_interval_s"]
        for right in ordered[i + 1:]:
            right_start, right_end = right["motion_interval_s"]
            if right_start - left_start > 1.0:
                break
            if left["colour"] != right["colour"]:
                continue
            if not set(left["candidate_ids"]).isdisjoint(right["candidate_ids"]):
                continue
            if min(left_end, right_end) <= max(left_start, right_start):
                continue
            if abs(left_end - right_end) > 5.0:
                continue
            if abs(left["span_px"] - right["span_px"]) > 0.01:
                continue
            first_distance = dist(left["first_pixel"], right["first_pixel"])
            last_distance = dist(left["last_pixel"], right["last_pixel"])
            if first_distance > 2.0 or last_distance > 2.0:
                continue
            pairs.append({
                "episode_ids": [left["episode_id"], right["episode_id"]],
                "colour": left["colour"],
                "motion_intervals_s": [left["motion_interval_s"], right["motion_interval_s"]],
                "candidate_ids": [left["candidate_ids"], right["candidate_ids"]],
                "first_pixel_distance_px": round(first_distance, 3),
                "last_pixel_distance_px": round(last_distance, 3),
                "same_physical_stone_verified": False,
            })
    return pairs
