"""A long static left image must be kept separate from titles and breaks."""

from scripts.audit_split_panel_freeze import static_runs


def test_static_run_keeps_pairwise_bounds_and_right_activity():
    rows = [
        {"previous_time_s": 0, "time_s": 5, "left_mae": 1, "right_mae": 1},
        {"previous_time_s": 5, "time_s": 10, "left_mae": 9, "right_mae": 9},
        {"previous_time_s": 10, "time_s": 15, "left_mae": 1.5, "right_mae": 12},
        {"previous_time_s": 15, "time_s": 20, "left_mae": 1.6, "right_mae": 14},
        {"previous_time_s": 20, "time_s": 25, "left_mae": 1.7, "right_mae": 16},
    ]
    runs = static_runs(rows, max_left_mae=3, min_duration_s=10)
    assert runs == [
        {
            "start_s": 10,
            "stop_s": 25,
            "duration_s": 15,
            "sample_edge_count": 3,
            "median_left_mae": 1.6,
            "median_right_mae": 14.0,
        }
    ]
