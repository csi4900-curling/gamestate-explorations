from prototype.unlinked_motion_rescue import find_adjacent_origin_proposals


SHOTS = [
    {"id": "S1", "interval_s": [0, 8]},
    {"id": "S2", "interval_s": [8, 20]},
]
ORIGINS = [{"shot_id": "S1", "interval_s": [0, 8], "probability": 0.96, "predicted": 0}]
EPISODES = [
    {
        "episode_id": "E1",
        "camera_shot_id": "S2",
        "colour": "yellow",
        "interval_s": [8.5, 14],
        "span_px": 40,
        "point_count": 5,
    }
]
LINKS = [{"episode_id": "E1", "candidate_ids": []}]


def test_unlinked_adjacent_motion_proposes_missing_origin_even_if_model_abstains():
    rows = find_adjacent_origin_proposals(LINKS, EPISODES, ORIGINS, SHOTS, [])
    assert len(rows) == 1
    assert rows[0]["candidate_status"] == "origin_absent_from_candidate_ledger"
    assert rows[0]["origin_model_predicted"] == 0
    assert rows[0]["physical_throw_verified"] is False


def test_colour_conflict_is_reviewed_but_same_colour_is_not():
    candidate = {"shot_id": "S1", "candidate_colour": "red", "counter_id": None}
    rows = find_adjacent_origin_proposals(LINKS, EPISODES, ORIGINS, SHOTS, [candidate])
    assert rows[0]["candidate_status"] == "existing_candidate_colour_conflict"
    candidate["candidate_colour"] = "yellow"
    assert find_adjacent_origin_proposals(LINKS, EPISODES, ORIGINS, SHOTS, [candidate]) == []


def test_late_or_already_linked_motion_is_not_a_rescue():
    episode = EPISODES[0] | {"interval_s": [10, 14]}
    assert find_adjacent_origin_proposals(LINKS, [episode], ORIGINS, SHOTS, []) == []
    assert (
        find_adjacent_origin_proposals(
            [{"episode_id": "E1", "candidate_ids": ["S1"]}], EPISODES, ORIGINS, SHOTS, []
        )
        == []
    )
