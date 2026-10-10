import pytest

from counter_sample_support import local_counter_support


def event():
    return {"id": "B01", "colour": "red", "crossing_time_s": 20,
            "remaining_before": [4, 2], "remaining_after": [3, 2]}


def test_repeated_underread_is_reported_without_rejecting_event():
    samples = [{"time_s": t, "counts": [4, 2] if t % 2 else [3, 2]}
               for t in range(8, 19)]
    samples += [{"time_s": t, "counts": [3, 2]} for t in range(22, 33)]
    result = local_counter_support(event(), samples)
    assert result["before"]["visible_samples"] == 11
    assert result["before"]["expected_samples"] == 5
    assert result["after"]["expected_fraction"] == 1
    assert result["before"]["distinct_states"] == [(3, 2), (4, 2)]


def test_no_visible_context_remains_unknown():
    result = local_counter_support(event(), [])
    assert result["before"]["expected_fraction"] is None
    assert result["after"]["expected_fraction"] is None
    with pytest.raises(ValueError, match="Invalid"):
        local_counter_support(event(), [], near_s=12, far_s=2)
