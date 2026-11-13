from prototype.scripts.probe_czech_reviewed_settle_gaps import roi_for_points, sample_indices


def test_sampling_includes_board_frame_after_half_second_steps():
    assert sample_indices(686.5, 687.0, 30) == [20595, 20610]
    assert sample_indices(100.0, 100.75, 30) == [3000, 3015, 3022]


def test_roi_covers_both_endpoints_and_clips_to_source():
    assert roi_for_points([[10, 15], [100, 120]], (1080, 1920)) == (0, 0, 166, 186)
