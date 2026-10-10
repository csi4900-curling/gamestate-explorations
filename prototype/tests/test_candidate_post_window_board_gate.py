from prototype.candidate_post_window_board_gate import post_window_sample_times


def test_post_window_gate_stops_before_next_candidate():
    assert post_window_sample_times([10, 20], 31) == [24.0, 26.0, 28.0]
    assert post_window_sample_times([10, 20], 25) == []
    assert post_window_sample_times([10, 20], 100)[0] == 24.0
    assert post_window_sample_times([10, 20], 100)[-1] == 50.0
