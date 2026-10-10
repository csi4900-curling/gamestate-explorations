from post_event_partial_board import stable_view_local_stones, tail_bounds


def frame(time_s, stones, status="registered"):
    return {
        "source_time_s": time_s,
        "status": status,
        "stones": [
            {"colour": colour, "view_local_ground_position_m": position}
            for colour, position in stones
        ],
    }


def test_tail_stops_before_next_candidate_even_if_path_overlaps_it():
    bounds = tail_bounds(2647.0, 2637.6, 2646.4, 2760.0)
    assert not bounds["eligible"]
    assert bounds["stop_s"] < bounds["start_s"]


def test_stable_board_requires_recent_supported_stone():
    rows = [frame(t, [("red", [0.2, 0.5])]) for t in (10, 12, 14, 16, 18)]
    board = stable_view_local_stones(rows)
    assert board["status"] == "partial_stable_view_local_board"
    assert len(board["stones"]) == 1
    assert board["stones"][0]["supporting_frame_count"] == 5
    assert board["stones"][0]["persistent_stone_identity"] is None
    disappeared = rows + [frame(20, []), frame(22, [])]
    assert stable_view_local_stones(disappeared)["stones"] == []


def test_rejected_registration_never_supplies_stability():
    rows = [
        frame(t, [("yellow", [0.0, 1.0])], status="insufficient_matches")
        for t in (10, 12, 14, 16, 18)
    ]
    board = stable_view_local_stones(rows)
    assert board["status"] == "no_registered_tail_frames"
    assert board["stones"] == []


def test_stationary_suffix_recovers_stone_after_it_slows():
    rows = [frame(10, [("yellow", [-1.34, 0.42])]), frame(11, [("yellow", [-1.33, 0.55])])]
    rows += [frame(t, [("yellow", [-1.32, 0.60])]) for t in (12, 13, 14, 15, 16, 17, 18)]
    assert stable_view_local_stones(rows)["stones"] == []
    board = stable_view_local_stones(rows, use_stable_suffix=True)
    assert len(board["stones"]) == 1
    assert board["stones"][0]["discarded_earlier_observations"] == 1
    assert board["stones"][0]["supporting_frame_count"] == 8


def test_stationary_suffix_does_not_promote_short_pause():
    rows = [frame(t, [("yellow", [t * 0.1, 0.5])]) for t in (10, 11, 12, 13)]
    rows += [frame(t, [("yellow", [1.0, 0.5])]) for t in (14, 15, 16)]
    assert stable_view_local_stones(rows, use_stable_suffix=True)["stones"] == []
