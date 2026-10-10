import pytest

from prototype.stable_display_run_context import attach_stable_display_runs


RUNS = [
    {"end": 1, "first_hit_s": 10, "last_hit_s": 90, "hit_count": 3},
    {"end": 2, "first_hit_s": 110, "last_hit_s": 190, "hit_count": 4},
]


def test_stable_display_runs_leave_unseen_transition_unassigned():
    events = [
        {"id": f"S{i}", "crossing_time_s": time, "colour": "red" if i % 2 else "yellow"}
        for i, time in enumerate((20, 100, 180), start=1)
    ]
    rows, counts = attach_stable_display_runs(events, RUNS)
    assert [row["displayed_end"] for row in rows] == [1, None, 2]
    assert rows[1]["display_context_status"] == "display_run_unobserved"
    assert all(
        row["physical_end_identity"] is None
        and not row["physical_throw_verified"]
        and not row["simulation_ready"]
        for row in rows
    )
    assert counts == {"1": {"red": 1}, "2": {"red": 1}}


def test_overlapping_runs_and_duplicate_events_fail():
    with pytest.raises(ValueError, match="overlap"):
        attach_stable_display_runs(
            [], RUNS + [{"end": 3, "first_hit_s": 180, "last_hit_s": 210, "hit_count": 2}]
        )
    duplicate = [{"id": "S1", "crossing_time_s": time, "colour": "red"} for time in (20, 30)]
    with pytest.raises(ValueError, match="Duplicate"):
        attach_stable_display_runs(duplicate, RUNS)
