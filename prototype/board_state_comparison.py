"""Compare video overhead stones with an official post-shot diagram."""

from math import dist

import numpy as np
from scipy.optimize import linear_sum_assignment


def compare_board_observations(
    video_stones, official_stones, *, official_house_center_y, max_match_distance=0.25
):
    """Match same-colour 2D symbols in unitless house-radius coordinates."""
    if official_house_center_y not in (160, 440):
        raise ValueError("Unknown official diagram orientation")
    lateral_sign = 1 if official_house_center_y == 440 else -1
    matches = []
    unmatched_video = []
    unmatched_official = []
    for colour in ("red", "yellow"):
        video = [row for row in video_stones if row["colour"] == colour]
        official = [row for row in official_stones if row["colour"] == colour]
        if not video:
            unmatched_official.extend(
                {"colour": colour, "official_index": index} for index in range(len(official))
            )
            continue
        if not official:
            unmatched_video.extend(
                {"colour": colour, "video_index": index} for index in range(len(video))
            )
            continue
        video_xy = [
            (row["canonical_lateral_house_radii"], row["longitudinal_house_radii"]) for row in video
        ]
        official_xy = [
            (lateral_sign * row["house_radius_coordinates"][0], row["house_radius_coordinates"][1])
            for row in official
        ]
        cost = np.asarray([[dist(a, b) for b in official_xy] for a in video_xy])
        indices = linear_sum_assignment(cost)
        used_video = set()
        used_official = set()
        for vi, oi in zip(*indices):
            error = float(cost[vi, oi])
            if error > max_match_distance:
                continue
            used_video.add(int(vi))
            used_official.add(int(oi))
            matches.append(
                {
                    "colour": colour,
                    "video_index": int(vi),
                    "official_index": int(oi),
                    "distance_house_radii": round(error, 4),
                    "video_xy": list(video_xy[vi]),
                    "official_xy": list(official_xy[oi]),
                }
            )
        unmatched_video.extend(
            {"colour": colour, "video_index": index}
            for index in range(len(video))
            if index not in used_video
        )
        unmatched_official.extend(
            {"colour": colour, "official_index": index}
            for index in range(len(official))
            if index not in used_official
        )
    errors = [row["distance_house_radii"] for row in matches]
    return {
        "video_stone_count": len(video_stones),
        "official_symbol_count": len(official_stones),
        "matched_count": len(matches),
        "mean_matched_distance_house_radii": round(sum(errors) / len(errors), 4)
        if errors
        else None,
        "max_matched_distance_house_radii": max(errors) if errors else None,
        "matches": matches,
        "unmatched_video": unmatched_video,
        "unmatched_official": unmatched_official,
    }
