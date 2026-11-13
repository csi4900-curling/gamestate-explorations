"""A post-entry board must not depend on arbitrary time within a crossing bracket."""

from scripts.export_right_only_partial_caps import anchors_agree


def observation(time_s, status, x=400):
    stable = (
        [{"local_observation_id": "C01", "colour": "red", "pixel_center": [x, 200]}]
        if status == "partial_stable_colour_cap_proposals"
        else []
    )
    return {"anchor_time_s": time_s, "observation_status": status, "stable_cap_proposals": stable}


def test_same_local_cap_across_entry_time_bracket_is_supported():
    central = observation(10.5, "partial_stable_colour_cap_proposals")
    assert anchors_agree(
        [
            observation(10, central["observation_status"], 402),
            central,
            observation(11, central["observation_status"], 399),
        ],
        central,
    )


def test_scene_flip_or_cap_jump_forces_abstention():
    central = observation(10.5, "partial_stable_colour_cap_proposals")
    assert not anchors_agree([observation(10, "abstain_scene_or_player_motion"), central], central)
    assert not anchors_agree(
        [observation(10, central["observation_status"], 420), central], central
    )
