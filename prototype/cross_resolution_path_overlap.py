"""Compare same-time receiving-view image paths at 1080p and 360p."""

from math import hypot
from statistics import median


def measure_temporal_pair_overlap(left_motion, right_proposals, corroboration, *, scale=3.0):
    """Measure pixel agreement, leaving physical identity entirely unverified."""
    if scale <= 0:
        raise ValueError("Scale must be positive")
    left_by_id = {row["candidate_id"]: row for row in left_motion}
    right_by_id = {"R01:" + row["raw_track_id"]: row for row in right_proposals}
    if len(left_by_id) != len(left_motion) or len(right_by_id) != len(right_proposals):
        raise ValueError("Duplicate left or right candidate ID")
    rows = []
    for link in corroboration:
        lid = link["left_candidate_id"]
        path = left_by_id[lid]["selection"].get("path", [])
        left_by_time = {point["source_time_s"]: point for point in path}
        if len(left_by_time) != len(path):
            raise ValueError(f"Duplicate left path time: {lid}")
        for match in link["matching_right_proposals"]:
            rid = match["right_proposal_id"]
            right_points = right_by_id[rid]["observed_prefix_points"]
            if len({point["time_s"] for point in right_points}) != len(right_points):
                raise ValueError(f"Duplicate right path time: {rid}")
            samples = []
            for point in right_points:
                time = point["time_s"]
                if time not in left_by_time:
                    continue
                lhs = left_by_time[time]["pixel_center"]
                rhs = point["pixel"]
                left_360 = [lhs[0] / scale, lhs[1] / scale]
                samples.append(
                    {
                        "source_time_s": time,
                        "left_continuation_pixel_360": [round(v, 3) for v in left_360],
                        "right_tracker_pixel_360": rhs,
                        "center_distance_px_360": round(
                            hypot(left_360[0] - rhs[0], left_360[1] - rhs[1]), 3
                        ),
                    }
                )
            distances = [sample["center_distance_px_360"] for sample in samples]
            rows.append(
                {
                    "left_candidate_id": lid,
                    "right_proposal_id": rid,
                    "view_order_lag_s": match["view_order_lag_s"],
                    "sampled_time_overlap_count": len(samples),
                    "median_center_distance_px_360": (
                        round(median(distances), 3) if distances else None
                    ),
                    "maximum_center_distance_px_360": (max(distances) if distances else None),
                    "samples": samples,
                    "same_observed_image_path_verified": False,
                    "physical_stone_identity_verified": False,
                }
            )
    if len({(r["left_candidate_id"], r["right_proposal_id"]) for r in rows}) != len(rows):
        raise ValueError("Duplicate temporal pair")
    return rows


def measure_all_co_sampled_pairs(
    left_motion, right_proposals, corroboration, *, scale=3.0, minimum_shared_samples=2
):
    """Return all co-sampled pairs, including nonlinked comparison controls."""
    if scale <= 0 or minimum_shared_samples < 1:
        raise ValueError("Invalid scale or sample requirement")
    linked = {
        (row["left_candidate_id"], match["right_proposal_id"])
        for row in corroboration
        for match in row["matching_right_proposals"]
    }
    rows = []
    for left in left_motion:
        path = left["selection"].get("path", [])
        by_time = {point["source_time_s"]: point for point in path}
        if len(by_time) != len(path):
            raise ValueError("Duplicate left path time")
        for right in right_proposals:
            rid = "R01:" + right["raw_track_id"]
            distances = []
            for point in right["observed_prefix_points"]:
                lhs = by_time.get(point["time_s"])
                if lhs is None:
                    continue
                rhs = point["pixel"]
                xy = lhs["pixel_center"]
                distances.append(hypot(xy[0] / scale - rhs[0], xy[1] / scale - rhs[1]))
            if len(distances) >= minimum_shared_samples:
                rows.append(
                    {
                        "left_candidate_id": left["candidate_id"],
                        "right_proposal_id": rid,
                        "shared_sample_count": len(distances),
                        "median_center_distance_px_360": round(median(distances), 3),
                        "temporal_colour_direction_link": (left["candidate_id"], rid) in linked,
                        "physical_stone_identity_verified": False,
                    }
                )
    return rows
