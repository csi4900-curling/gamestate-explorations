import pytest

from temporal_edit_isolation import edit_isolation


def metric(gray, hist):
    return {"gray_change": gray, "hist_distance": hist}


def test_isolated_peak_and_sustained_visual_change_are_distinct():
    sharp = edit_isolation(metric(1, .02), metric(70, .3), metric(5, .05))
    assert sharp["isolated_spike"]
    assert sharp["gray_isolation_ratio"] == 14
    assert sharp["hist_isolation_ratio"] == 6
    broad = edit_isolation(metric(60, .2), metric(70, .3), metric(50, .22))
    assert not broad["isolated_spike"]


def test_zero_neighbors_are_bounded_and_invalid_metrics_rejected():
    result = edit_isolation(metric(0, 0), metric(60, .25), metric(0, 0))
    assert result["gray_isolation_ratio"] == 60
    assert result["hist_isolation_ratio"] == 250
    with pytest.raises(ValueError):
        edit_isolation(metric(-1, 0), metric(60, .25), metric(0, 0))
