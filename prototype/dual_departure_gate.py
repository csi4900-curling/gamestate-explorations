"""Route mirrored early-ice cap gates using source-only motion evidence."""

from departure_gate_decision import decide_gate_colour


def motion_points(row):
    return sum(
        track["point_count"] for colour in ("red", "yellow") for track in row["transits"][colour]
    )


def route_gate_sides(paired_rows):
    """Select a side per origin shot, keeping the last motion-supported side.

    Each row contains `left` and `right` gate observations for the same camera
    shot. No scoreboard end number, counter colour or official shot is used.
    """
    state = None
    output = []
    for pair in paired_rows:
        left, right = pair["left"], pair["right"]
        left_points, right_points = motion_points(left), motion_points(right)
        if left_points >= 3 and left_points >= 2 * max(1, right_points):
            side, route = "left", "motion_selected_side"
            state = side
        elif right_points >= 3 and right_points >= 2 * max(1, left_points):
            side, route = "right", "motion_selected_side"
            state = side
        elif state is not None:
            side, route = state, "carried_motion_selected_side"
        else:
            left_count = sum(left["gate_counts"].values())
            right_count = sum(right["gate_counts"].values())
            if left_count == right_count:
                side, route = None, "orientation_abstention"
            else:
                side, route = (
                    "left" if left_count > right_count else "right",
                    "initial_count_selected_side",
                )
        choice = (
            decide_gate_colour(pair[side])
            if side
            else {"colour": None, "route": "orientation_abstention", "anchor_s": None}
        )
        output.append(
            {
                "shot_id": pair["shot_id"],
                "interval_s": pair["interval_s"],
                "side": side,
                "side_route": route,
                "left_motion_points": left_points,
                "right_motion_points": right_points,
                "left_gate_count": sum(left["gate_counts"].values()),
                "right_gate_count": sum(right["gate_counts"].values()),
                "colour": choice["colour"],
                "colour_route": choice["route"],
                "early_gate_anchor_s": choice["anchor_s"],
            }
        )
    return output
