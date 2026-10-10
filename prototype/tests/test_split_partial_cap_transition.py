import pytest

from prototype.split_partial_cap_transition import (
    compare_cap_sets,
    compare_observation_rows,
)


def cap(local_id, colour, x, y):
    return {"local_observation_id": local_id, "colour": colour, "pixel_center": [x, y]}


def row(candidate_id, status, caps):
    return {
        "candidate_id": candidate_id,
        "observation_status": status,
        "coordinate_frame": "source_right_camera_pixels_not_metric",
        "stable_cap_proposals": caps,
    }


def test_partial_delta_preserves_additions_losses_and_nearby_matches():
    delta = compare_cap_sets(
        [cap("B1", "red", 400, 200), cap("B2", "yellow", 450, 210)],
        [cap("A1", "red", 402, 201), cap("A2", "yellow", 500, 200)],
    )
    assert len(delta["locally_retained"]) == 1
    assert delta["no_longer_observed"] == ["B2"]
    assert delta["newly_observed"] == ["A2"]
    assert not delta["physical_transition_verified"]


def test_ambiguous_same_colour_neighbours_stay_unresolved():
    delta = compare_cap_sets(
        [cap("B1", "red", 400, 200), cap("B2", "red", 402, 200)], [cap("A1", "red", 401, 200)]
    )
    assert delta["locally_retained"] == []
    assert delta["unresolved_before"] == ["B1", "B2"]
    assert delta["unresolved_after"] == ["A1"]
    assert delta["newly_observed"] == []


def test_scene_or_window_abstention_keeps_transition_unknown():
    before = row("left:L1", "partial_stable_colour_cap_proposals", [])
    after = row("left:L1", "no_stable_colour_cap_proposals", [])
    assert compare_observation_rows(before, after, 25)["comparison_status"] == (
        "abstain_cross_window_scene_change"
    )
    before["observation_status"] = "abstain_previous_left_event"
    assert compare_observation_rows(before, after, None)["comparison_status"] == (
        "abstain_pre_or_post_window"
    )
    with pytest.raises(ValueError, match="Invalid cross-window"):
        compare_observation_rows(after, after, None)
