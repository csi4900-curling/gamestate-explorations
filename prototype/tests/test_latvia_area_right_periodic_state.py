from prototype.scripts.join_latvia_area_right_periodic_state import following_windows


def test_following_partial_window_never_crosses_next_candidate():
    windows = [{"anchor_time_s": second} for second in (110, 115, 125, 130, 135)]
    assert [
        row["anchor_time_s"]
        for row in following_windows(windows, passage_s=100, next_proposal_s=135)
    ] == [115, 125, 130]


def test_following_window_is_empty_when_next_candidate_is_too_close():
    windows = [{"anchor_time_s": second} for second in (110, 120, 130)]
    assert following_windows(windows, passage_s=100, next_proposal_s=118) == []
