"""Combine directional moving-stone evidence without promoting it to game state."""


def _usable(selection):
    status = selection["status"]
    if status == "provisional_unique_far_entry_motion_path":
        return "provisional_moving_phase", selection["path"]
    if status == "ambiguous_far_entry_motion_paths" and selection.get("shared_prefix"):
        return "provisional_prefix_before_identity_ambiguity", selection["shared_prefix"]
    return None, []


def combine_directional_event(row, left_override=None):
    """Select one supported receiving view, or retain conflict/absence."""
    right = row["far_entry_selection"]
    left = left_override if left_override is not None else row["left_reverse_selection"]
    right_kind, right_path = _usable(right)
    left_kind, left_path = _usable(left)
    if right_path and left_path:
        status, view, path = "conflicting_receiving_view_evidence", None, []
    elif right_path:
        status, view, path = right_kind, "right", right_path
    elif left_path:
        status, view, path = left_kind, "left", left_path
    else:
        status, view, path = "no_supported_motion_evidence", None, []
    return {
        "event_id": row["event_id"],
        "reference_colour": row["reference_colour"],
        "reference_window_s": row["reference_window_s"],
        "status": status,
        "receiving_view": view,
        "first_observation_s": path[0]["source_time_s"] if path else None,
        "last_observation_s": path[-1]["source_time_s"] if path else None,
        "sample_count": len(path),
        "observed_path": path,
        "right_selection_status": right["status"],
        "left_selection_status": left["status"],
        "first_identity_ambiguity_s": (
            right.get("first_ambiguity_time_s") if view == "right" else
            left.get("first_ambiguity_time_s") if view == "left" else None),
        "release_time_observed": False,
        "settled_board_observed": False,
        "physical_identity_verified": False,
        "metric_accuracy_verified": False,
        "simulation_ready": False,
    }
