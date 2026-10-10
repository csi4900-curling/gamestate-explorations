from prototype.wide_roi_continuation import next_observation


PATH = [{"time_s": 1.0, "pixel": [100, 100]},
        {"time_s": 1.1, "pixel": [100, 103]},
        {"time_s": 1.2, "pixel": [100, 106]}]


def test_unique_nearby_motion_continues():
    point, status = next_observation(PATH, [{"pixel": [100, 109]}], 1.3)
    assert status == "continued"
    assert point["time_s"] == 1.3


def test_ambiguous_or_distant_candidate_stops():
    assert next_observation(PATH, [{"pixel": [100, 109]},
                                   {"pixel": [102, 109]}], 1.3)[1] == \
        "ambiguous_nearby_caps"
    assert next_observation(PATH, [{"pixel": [200, 200]}], 1.3)[1] == \
        "no_nearby_same_colour_cap"
