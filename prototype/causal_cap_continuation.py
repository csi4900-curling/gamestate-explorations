"""Conservative one-step image-cap association without future board positions."""

from math import dist


def choose_next_cap(
    current_center,
    previous_center,
    dt_ratio,
    components,
    *,
    max_prediction_error_px=65,
    max_step_px=110,
    max_step_growth=1.8,
    step_growth_allowance_px=12,
    min_margin_px=15,
    min_ratio=1.5,
):
    """Return a unique nearby component or an explicit abstention.

    The caller supplies only past positions and components in the current frame.
    Geometric uniqueness is not proof that the component is the same stone.
    """
    prediction = [
        current_center[i] + (current_center[i] - previous_center[i]) * dt_ratio for i in (0, 1)
    ]
    prior_step = dist(current_center, previous_center)
    relative_step_limit = max_step_growth * prior_step * dt_ratio + step_growth_allowance_px
    eligible = []
    for component in components:
        center = component["centroid_px_1080"]
        prediction_error = dist(center, prediction)
        step = dist(center, current_center)
        if (
            prediction_error <= max_prediction_error_px
            and step <= max_step_px
            and step <= relative_step_limit
        ):
            eligible.append((prediction_error, step, component))
    eligible.sort(key=lambda item: (item[0], item[1]))
    if not eligible:
        return {
            "status": "no_cap_inside_motion_gate",
            "prediction_px": prediction,
            "relative_step_limit_px": round(relative_step_limit, 3),
            "eligible_count": 0,
            "selected": None,
        }
    best = eligible[0]
    if len(eligible) > 1:
        runner_up = eligible[1]
        if runner_up[0] - best[0] < min_margin_px or runner_up[0] < min_ratio * best[0]:
            return {
                "status": "competing_caps_inside_motion_gate",
                "prediction_px": prediction,
                "relative_step_limit_px": round(relative_step_limit, 3),
                "eligible_count": len(eligible),
                "selected": None,
                "best_prediction_error_px": round(best[0], 3),
                "runner_up_prediction_error_px": round(runner_up[0], 3),
            }
    return {
        "status": "unique_motion_gate_choice",
        "prediction_px": prediction,
        "relative_step_limit_px": round(relative_step_limit, 3),
        "eligible_count": len(eligible),
        "selected": best[2],
        "prediction_error_px": round(best[0], 3),
        "step_px": round(best[1], 3),
    }
