from scripts.export_china_board_union_handoff import temporal_relation


def test_board_travel_relation_distinguishes_overlap_from_following_snapshot():
    assert temporal_relation([1620.0, 1624.0], [1611.8, 1624.4]) == (
        "overlaps_observed_travel_interval")
    assert temporal_relation([3500.0, 3508.0], [3464.0, 3477.2]) == (
        "board_observation_after_travel")
    assert temporal_relation([10.0, 12.0], [14.0, 20.0]) == (
        "board_observation_before_travel")
    assert temporal_relation(None, [14.0, 20.0]) == "no_comparable_travel_interval"
