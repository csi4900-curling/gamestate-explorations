from prototype.postcut_colour_support import camera_motion_status, resolve_postcut_colour


def test_prefers_unique_strict_motion_and_abstains_when_both_colours_move():
    assert resolve_postcut_colour(
        {"red": {"strict": 0, "relaxed": 2}, "yellow": {"strict": 1, "relaxed": 1}}
    ) == {"colour": "yellow", "status": "unique_strict_postcut_motion"}
    assert (
        resolve_postcut_colour(
            {"red": {"strict": 1, "relaxed": 1}, "yellow": {"strict": 1, "relaxed": 1}}
        )["colour"]
        is None
    )
    assert resolve_postcut_colour(
        {"red": {"strict": 0, "relaxed": 1}, "yellow": {"strict": 0, "relaxed": 0}}
    ) == {"colour": "red", "status": "unique_relaxed_postcut_motion"}


def test_camera_registration_only_rejects_reliably_static_track():
    def row(value, reliable=True):
        return {"camera_residual_px": value, "registration_reliable": reliable}

    assert camera_motion_status([row(0.8), row(1.2)]) == "camera_explained_static"
    assert camera_motion_status([row(0.8), row(7)]) == "relative_motion_or_identity_change"
    assert camera_motion_status([row(None, False), row(1.2)]) == "camera_motion_unresolved"
