"""Pairing keeps cross-view evidence separate from release timing."""

from origin_receiver_pairing import pair_origin_receiver


def shot(identifier, tracks):
    return {"shot_id": identifier, "interval_s": [0, 10], "transits": tracks}


def track(colour, points):
    return {"colour": colour, "point_count": points, "interval_s": [4, 5], "displacement_px": 80}


def test_shared_colour_resolves_wrong_top_origin_colour():
    shots = [shot("S1", [track("red", 7), track("yellow", 4)]), shot("S2", [track("yellow", 3)])]
    origins = {
        "S1": {"predicted": 1, "probability": 0.9},
        "S2": {"predicted": 0, "probability": 0.1},
    }
    events = pair_origin_receiver(shots, origins)
    assert len(events) == 1
    assert events[0]["colour"] == "yellow"
    assert events[0]["evidence_route"] == "same_colour_across_adjacent_camera_shots"
    assert events[0]["release_window_s"] == [0, 10]


def test_receiving_only_support_keeps_broad_release_window():
    shots = [shot("S1", []), shot("S2", [track("red", 5)])]
    origins = {
        "S1": {"predicted": 1, "probability": 0.8},
        "S2": {"predicted": 0, "probability": 0.1},
    }
    (event,) = pair_origin_receiver(shots, origins)
    assert event["receiving_shot_id"] == "S2"
    assert event["release_window_s"] == [0, 10]
    assert event["evidence_route"] == "receiving_shot_visual_only"


def test_no_motion_does_not_create_event():
    assert (
        pair_origin_receiver([shot("S1", [])], {"S1": {"predicted": 1, "probability": 0.9}}) == []
    )
