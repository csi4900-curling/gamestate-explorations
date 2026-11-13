import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from motion_correspondence import join_passages_to_motion


def passage(pid, time, colour="red", direction="negative_y"):
    return {"id": pid, "crossing_time_s": time, "colour": colour, "view_motion": direction}


def motion(eid, time, colour="red", view="right"):
    return {
        "event_id": eid,
        "first_observation_s": time,
        "reference_colour": colour,
        "receiving_view": view,
        "status": "provisional_moving_phase",
    }


def test_unique_link_and_unmatched_candidate():
    result = join_passages_to_motion([passage("D1", 10), passage("D2", 20)], [motion("C1", 14)])
    assert result["passages"][0]["linked_reference_event_ids"] == ["C1"]
    assert result["passages"][1]["status"] == "no_window_conditioned_motion_support"


def test_ambiguous_prior_passages_do_not_get_assigned():
    result = join_passages_to_motion([passage("D1", 10), passage("D2", 11)], [motion("C1", 14)])
    assert result["paths"][0]["status"] == "ambiguous_multiple_passages"
    assert all(not row["linked_reference_event_ids"] for row in result["passages"])


def test_colour_view_and_time_must_agree():
    result = join_passages_to_motion(
        [passage("D1", 10, "yellow"), passage("D2", 10, "red", "positive_y"), passage("D3", 1)],
        [motion("C1", 14)],
    )
    assert result["paths"][0]["status"] == "no_compatible_passage"
    with pytest.raises(ValueError):
        join_passages_to_motion([passage("D1", 1), passage("D1", 2)], [])
