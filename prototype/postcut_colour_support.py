"""Choose a handle colour only from unique motion in the receiving view."""


def camera_motion_status(rows, *, min_reliable_pairs=2, max_static_residual_px=3):
    """Reject a track only when reliable background fits explain its motion."""
    residuals = [
        row["camera_residual_px"]
        for row in rows
        if row["registration_reliable"] and row["camera_residual_px"] is not None
    ]
    if len(residuals) < min_reliable_pairs:
        return "camera_motion_unresolved"
    return (
        "camera_explained_static"
        if max(residuals) <= max_static_residual_px
        else "relative_motion_or_identity_change"
    )


def resolve_postcut_colour(tracks_by_colour):
    """Return a cautious colour decision from strict then relaxed tracks.

    Each colour maps to strict and relaxed track counts after a known cut.
    The decision is only visual support, not throw identity confirmation.
    """
    if set(tracks_by_colour) != {"red", "yellow"}:
        raise ValueError("Both stone colours are required")
    strict = [colour for colour in ("red", "yellow") if tracks_by_colour[colour]["strict"] > 0]
    if len(strict) == 1:
        return {"colour": strict[0], "status": "unique_strict_postcut_motion"}
    if len(strict) == 2:
        return {"colour": None, "status": "ambiguous_strict_postcut_motion"}
    relaxed = [colour for colour in ("red", "yellow") if tracks_by_colour[colour]["relaxed"] > 0]
    if len(relaxed) == 1:
        return {"colour": relaxed[0], "status": "unique_relaxed_postcut_motion"}
    return {"colour": None, "status": "ambiguous_or_absent_postcut_motion"}
