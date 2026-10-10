from prototype.scripts.scan_full_match_split_post_event_caps import eligible_times


def test_post_event_samples_respect_next_candidate_and_run_boundary():
    assert eligible_times(100, 140, 200) == ([115, 120, 125], None)
    assert eligible_times(100, 129, 200) == (None, "abstain_next_left_event")
    assert eligible_times(100, None, 125) == (None, "abstain_run_boundary")


def test_post_event_guard_does_not_cross_runs():
    assert eligible_times(90, None, 110) == (None, "abstain_run_boundary")
