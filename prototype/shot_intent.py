"""Explicit intent semantics: never equate an aiming broom with a resting target."""

import numpy as np


def final_position_error(intent, outcome):
    """Return a geometric draw/guard residual only with reviewed destination evidence.

    This measures execution relative to an observed intent, not CV accuracy. The latter
    additionally needs independent position references. Unknown uncertainty stays unknown.
    """
    if intent.get("kind") != "resting_destination":
        return {
            "status": "unavailable",
            "error_m": None,
            "reason": "An aiming line or unknown gesture is not a resting destination.",
        }
    if not intent.get("reviewed") or not intent.get("evidence"):
        return {
            "status": "unavailable",
            "error_m": None,
            "reason": "Destination interpretation requires reviewed source evidence.",
        }
    if intent.get("shot_type") not in ("draw", "guard"):
        return {
            "status": "unavailable",
            "error_m": None,
            "reason": "Collision shots require task-specific outcome measures.",
        }
    if not outcome.get("settled") or outcome.get("interaction_detected") is not False:
        return {
            "status": "unavailable",
            "error_m": None,
            "reason": "No supported collision-free settled outcome.",
        }
    if not intent.get("coordinate_frame") or intent.get("coordinate_frame") != outcome.get(
        "coordinate_frame"
    ):
        return {
            "status": "unavailable",
            "error_m": None,
            "reason": "Coordinates must share a verified frame.",
        }
    target = intent.get("position_m")
    actual = outcome.get("position_m")
    if target is None or actual is None:
        return {
            "status": "unavailable",
            "error_m": None,
            "reason": "Metric target or outcome missing.",
        }
    try:
        target = np.asarray(target, float)
        actual = np.asarray(actual, float)
    except (TypeError, ValueError):
        return {"status": "unavailable", "error_m": None, "reason": "Invalid position."}
    if target.shape != (2,) or actual.shape != (2,) or not np.isfinite(np.r_[target, actual]).all():
        return {"status": "unavailable", "error_m": None, "reason": "Invalid position."}
    delta = actual - target
    return {
        "status": "conditional_geometric_residual",
        "error_m": float(np.linalg.norm(delta)),
        "delta_xy_m": delta.tolist(),
        "uncertainty_m": None,
        "note": "Execution residual against interpreted intent; not independent measurement accuracy or an official shot score.",
    }
