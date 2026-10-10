import pytest

from prototype.cut_effect_audit import audit_cut_effects


def origin(shot, start, end, predicted, probability):
    return {
        "shot_id": shot,
        "interval_s": [start, end],
        "predicted": predicted,
        "probability": probability,
    }


def test_origin_rescue_pattern_uses_time_mapping():
    edit = [{"time_s": 5.0, "isolated_spike": True}]
    old = [origin("S1", 0, 10, 0, 0.3)]
    new = [origin("S1", 0, 5, 0, 0.1), origin("S2", 5, 10, 1, 0.9)]
    result = audit_cut_effects(edit, old, new)
    assert result["origin_pattern_counts"] == {"001": 1}
    assert result["rows"][0]["right"]["origin_probability"] == 0.9


def test_missing_boundary_rejected():
    with pytest.raises(ValueError, match="unique"):
        audit_cut_effects(
            [{"time_s": 5, "isolated_spike": True}], [origin("S1", 0, 10, 0, 0.3)], []
        )
