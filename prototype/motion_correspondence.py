"""Conservative passage-to-receiving-motion correspondence for split views."""


def join_passages_to_motion(passages, motion_rows, max_delay_s=6.0):
    """Link a path only when exactly one earlier compatible passage exists.

    This does not score a detector: motion paths may themselves be selected
    using development reference windows and are not independent truth.
    """
    if max_delay_s <= 0:
        raise ValueError("Maximum delay must be positive")
    by_id = {p["id"]: p for p in passages}
    if len(by_id) != len(passages):
        raise ValueError("Duplicate passage IDs")
    links = {p["id"]: [] for p in passages}
    path_rows = []
    view_direction = {"left": "positive_y", "right": "negative_y"}
    for motion in motion_rows:
        view = motion["receiving_view"]
        start = motion["first_observation_s"]
        if view not in view_direction or start is None:
            path_rows.append(
                {
                    "reference_event_id": motion["event_id"],
                    "status": "no_usable_receiving_path",
                    "compatible_passage_ids": [],
                }
            )
            continue
        eligible = [
            p
            for p in passages
            if p["colour"] == motion["reference_colour"]
            and p["view_motion"] == view_direction[view]
            and 0 <= start - p["crossing_time_s"] <= max_delay_s
        ]
        path_status = (
            "unique_temporal_colour_view_match"
            if len(eligible) == 1
            else "ambiguous_multiple_passages"
            if eligible
            else "no_compatible_passage"
        )
        path_rows.append(
            {
                "reference_event_id": motion["event_id"],
                "status": path_status,
                "compatible_passage_ids": [p["id"] for p in eligible],
                "receiving_view": view,
                "path_first_observation_s": start,
                "path_status": motion["status"],
            }
        )
        if len(eligible) == 1:
            links[eligible[0]["id"]].append(motion["event_id"])
    passage_rows = []
    for passage in passages:
        matched = links[passage["id"]]
        passage_rows.append(
            {
                "passage_id": passage["id"],
                "colour": passage["colour"],
                "crossing_time_s": passage["crossing_time_s"],
                "view_motion": passage["view_motion"],
                "status": (
                    "unique_window_conditioned_motion_support"
                    if len(matched) == 1
                    else "ambiguous_multiple_motion_paths"
                    if matched
                    else "no_window_conditioned_motion_support"
                ),
                "linked_reference_event_ids": matched,
                "physical_stone_identity_verified": False,
            }
        )
    return {"passages": passage_rows, "paths": path_rows}
