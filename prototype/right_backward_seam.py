"""Conditionally extend a right-camera prefix back toward a left-camera track."""

from math import ceil, hypot


def choose_backward_point(
    anchor,
    proposals,
    *,
    max_step_px=35,
    min_upward_forward_px=5,
    min_area_ratio=0.4,
    max_area_ratio=3,
):
    """Return one plausible earlier colour blob, or an explicit abstention."""
    choices = []
    for proposal in proposals:
        dx = proposal["pixel"][0] - anchor["pixel"][0]
        dy = proposal["pixel"][1] - anchor["pixel"][1]
        area_ratio = proposal["cap_area_px2"] / anchor["cap_area_px2"]
        distance = hypot(dx, dy)
        if (
            dy >= min_upward_forward_px
            and distance <= max_step_px
            and min_area_ratio <= area_ratio <= max_area_ratio
        ):
            choices.append((distance, proposal))
    if len(choices) != 1:
        return None, "no_directional_colour_blob" if not choices else "ambiguous_directional_blobs"
    return choices[0][1], "unique_directional_colour_blob"


def backward_extension(first_point, left_end_s, colour, sample_proposals, *, max_lookback_s=8):
    """Follow unique image blobs backward; never infer unseen positions."""
    anchor = first_point
    trace = []
    status = "reached_left_observation_end"
    earliest = max(ceil(left_end_s), int(first_point["time_s"] - max_lookback_s))
    for time_s in range(int(first_point["time_s"]) - 1, earliest - 1, -1):
        chosen, reason = choose_backward_point(anchor, sample_proposals(time_s, colour))
        if chosen is None:
            status = reason
            break
        anchor = {**chosen, "time_s": float(time_s)}
        trace.append(anchor)
    else:
        if trace and trace[-1]["time_s"] > left_end_s:
            status = "lookback_limit_or_last_integer_before_left_end"
    return {
        "new_first_observed_s": anchor["time_s"],
        "added_observations": list(reversed(trace)),
        "stop_reason": status,
        "physical_identity_verified": False,
    }
