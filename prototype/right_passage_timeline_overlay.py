"""Conservative cross-view overlay for reviewed right passages and left events."""

from collections import Counter


def build_overlay(left_events, right_proposals, source_classes, *, max_lag_s=20):
    """Link only unique direction-aware left events to short right stone paths.

    Every right proposal remains in the output. The match is temporal/colour
    corroboration, never a physical identity or verified throw decision.
    """
    if max_lag_s <= 0:
        raise ValueError("Positive lag window required")
    left_ids = [row["id"] for row in left_events]
    right_ids = [row["raw_track_id"] for row in right_proposals]
    if len(left_ids) != len(set(left_ids)) or len(right_ids) != len(set(right_ids)):
        raise ValueError("Duplicate event or proposal ID")
    if set(right_ids) != set(source_classes):
        raise ValueError("Every right proposal needs one source class")

    rows = []
    for right in right_proposals:
        raw_id = right["raw_track_id"]
        cls = source_classes[raw_id]
        t = right["passage"]["time_s"]
        direction = right["direction"]
        candidates = sorted(
            (
                left
                for left in left_events
                if left["colour"] == right["colour_claim"]
                and (
                    (direction == "negative_y" and 0 <= t - left["crossing_time_s"] <= max_lag_s)
                    or (direction == "positive_y" and 0 <= left["crossing_time_s"] - t <= max_lag_s)
                )
            ),
            key=lambda left: abs(t - left["crossing_time_s"]),
        )
        if cls in (
            "person_or_wheelchair",
            "person_wheelchair_or_clothing",
            "moving_person_wheelchair",
        ):
            status = "source_reviewed_person_candidate"
        elif cls == "stone_pixels_identity_uncertain":
            status = "stone_pixels_long_track_identity_review"
        elif cls != "moving_stone":
            status = "source_class_review"
        elif direction not in ("negative_y", "positive_y"):
            status = "right_direction_review"
        elif len(candidates) == 0:
            status = "right_stone_without_directional_left_review"
        elif len(candidates) > 1:
            status = "multiple_directional_left_events_review"
        else:
            status = "unique_time_colour_corrob"
        rows.append(
            {
                "right_raw_track_id": raw_id,
                "right_source_prefix_class": cls,
                "right_colour_claim": right["colour_claim"],
                "right_direction": direction,
                "right_passage_time_s": t,
                "right_observed_prefix_interval_s": right["observed_prefix_interval_s"],
                "right_observed_prefix_points": right["observed_prefix_points"],
                "direction_aware_same_colour_left_ids_within_lag": [
                    left["id"] for left in candidates
                ],
                "left_minus_right_time_s_if_unique_candidate": (
                    round(candidates[0]["crossing_time_s"] - t, 3) if len(candidates) == 1 else None
                ),
                "conditional_left_event_id": (
                    candidates[0]["id"] if status == "unique_time_colour_corrob" else None
                ),
                "fusion_status": status,
                "physical_cross_view_identity_verified": False,
                "simulation_ready": False,
            }
        )
    links = Counter(
        row["conditional_left_event_id"] for row in rows if row["conditional_left_event_id"]
    )
    for row in rows:
        if row["conditional_left_event_id"] and links[row["conditional_left_event_id"]] > 1:
            row["fusion_status"] = "multiple_right_stone_paths_review"
            row["conditional_left_event_id"] = None
    linked = {row["conditional_left_event_id"] for row in rows if row["conditional_left_event_id"]}
    return {
        "rows": rows,
        "left_events_without_short_right_link": [
            row["id"] for row in left_events if row["id"] not in linked
        ],
    }
