"""Pair simultaneous 360p cap and 1080p body observations in one camera."""

from statistics import median


def matched_point_offsets(low_points, high_points):
    high_by_time = {row["time_s"]: row for row in high_points}
    if len(high_by_time) != len(high_points):
        raise ValueError("Duplicate high-resolution source time")
    pairs = []
    for low in low_points:
        high = high_by_time.get(low["time_s"])
        if high is None:
            continue
        hx, hy = high["center_1080p_px"]
        lx, ly = low["pixel"]
        pairs.append({"source_time_s": low["time_s"],
                      "cap_center_360p_px": low["pixel"],
                      "body_center_1080p_px": high["center_1080p_px"],
                      "body_minus_cap_x_360p_px": round(hx / 3 - lx, 3),
                      "body_minus_cap_y_360p_px": round(hy / 3 - ly, 3)})
    return pairs


def compatible_body_path(low_points, high_points, *, min_common=2,
                         max_abs_x_offset_360p_px=12,
                         min_y_offset_360p_px=0,
                         max_y_offset_360p_px=16):
    pairs = matched_point_offsets(low_points, high_points)
    if (len(pairs) < min_common or
            any(abs(row["body_minus_cap_x_360p_px"]) >
                max_abs_x_offset_360p_px or
                not min_y_offset_360p_px <= row[
                    "body_minus_cap_y_360p_px"] <= max_y_offset_360p_px
                for row in pairs)):
        return None
    return {
        "common_observation_count": len(pairs),
        "median_body_minus_cap_x_360p_px": round(median(
            row["body_minus_cap_x_360p_px"] for row in pairs), 3),
        "median_body_minus_cap_y_360p_px": round(median(
            row["body_minus_cap_y_360p_px"] for row in pairs), 3),
        "synchronous_points": pairs,
    }
