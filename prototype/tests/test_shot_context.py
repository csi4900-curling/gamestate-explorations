import pytest

from shot_context import shot_for_time, shot_intervals


def test_shots_partition_source_at_hard_cuts():
    intervals = shot_intervals(10, 20, [17, 13])
    assert intervals == [[10, 13], [13, 17], [17, 20]]
    assert shot_for_time(intervals, 12.9) == 0
    assert shot_for_time(intervals, 13) == 1
    assert shot_for_time(intervals, 17) == 2
    with pytest.raises(ValueError):
        shot_for_time(intervals, 20)


def test_invalid_cut_boundary_is_rejected():
    with pytest.raises(ValueError):
        shot_intervals(10, 20, [10])
    with pytest.raises(ValueError):
        shot_intervals(10, 20, [15, 15])
