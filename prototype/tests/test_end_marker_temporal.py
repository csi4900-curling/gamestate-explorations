import pytest

from prototype.end_marker_temporal import stable_marker_evidence


def row(time_s, end):
    return {"time_s": time_s, "marker": {"end": end} if end is not None else None}


def test_single_spurious_backward_read_does_not_create_boundary():
    result = stable_marker_evidence([
        row(0, 3), row(10, 3), row(20, None), row(30, 1),
        row(40, 3), row(50, 3), row(60, 4), row(70, 4),
    ])
    assert [run["end"] for run in result["stable_runs"]] == [3, 4]
    assert result["discarded_short_runs"] == [
        {"end": 1, "first_hit_s": 30, "last_hit_s": 30, "hit_count": 1}]
    assert result["stable_marker_changes"] == [
        {"from_end": 3, "to_end": 4, "last_old_hit_s": 50, "first_new_hit_s": 60}]


def test_missing_end_is_not_inserted():
    result = stable_marker_evidence([row(0, 2), row(10, 2), row(20, 4), row(30, 4)])
    assert result["stable_marker_changes"][0]["to_end"] == 4


def test_invalid_threshold_and_time_order_rejected():
    with pytest.raises(ValueError, match="two"):
        stable_marker_evidence([], min_hits=1)
    with pytest.raises(ValueError, match="increasing"):
        stable_marker_evidence([row(10, 1), row(10, 2)])
