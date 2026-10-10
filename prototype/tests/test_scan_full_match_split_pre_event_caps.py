from prototype.scripts.scan_full_match_split_pre_event_caps import eligible_times


def test_pre_event_samples_respect_previous_candidate_and_run_boundary():
    assert eligible_times(100, 60, 0) == ([75, 80, 85], None)
    assert eligible_times(100, 72, 0) == (None, "abstain_previous_left_event")
    assert eligible_times(100, None, 80) == (None, "abstain_run_boundary")
