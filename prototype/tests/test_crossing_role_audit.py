from scripts.audit_crossing_roles import four_sample_role


def test_isolated_reversal_does_not_reverse_the_role():
    samples = [{"time_s": index/10, "conditional_height_adjusted_position_m": [0, distance]}
               for index, distance in enumerate([-10.54, -10.32, -10.34, -10.12])]
    assert four_sample_role(samples, [0.1, 0.2], 0.1) == "receiving"


def test_missing_geometry_or_frame_or_tee_crossing_abstains():
    def classify(times, positions):
        samples = [{"time_s": time, "conditional_height_adjusted_position_m": pos}
                   for time, pos in zip(times, positions)]
        return four_sample_role(samples, [0.1, 0.2], 0.1)

    assert classify([0, .1, .2, .3], [[0, 1], None, [0, 2], [0, 3]]) == "unassigned"
    assert classify([0, .1, .2, .4], [[0, 1], [0, 2], [0, 3], [0, 4]]) == "unassigned"
    assert classify([0, .1, .2, .3], [[0, -1], [0, 0], [0, 1], [0, 2]]) == "unassigned"
