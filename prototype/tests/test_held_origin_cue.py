"""Held and short-moving stones remain visible as different evidence types."""

from held_origin_cue import central_cap_candidates, summarize_held_origin


def point(colour, x, y, score=0.1):
    return {"colour": colour, "pixel": [x, y], "patch_score": score,
            "bbox": [x - 10, y - 5, 20, 10]}


def test_mirrored_corridor_excludes_player_region():
    candidates = [point("yellow", 365, 311, -1.4),
                  point("red", 306, 356, 0.2)]
    assert central_cap_candidates(candidates, "right") == candidates[:1]
    assert central_cap_candidates(candidates, "left") == []


def test_stationary_hold_and_fast_movement_are_separate():
    rows = [(i * 0.2, [point("yellow", 365, 311)]) for i in range(10)]
    rows += [(2.0, [point("red", 310, 300)]),
             (2.2, [point("red", 335, 310)]),
             (2.6, [point("red", 365, 320)])]
    result = summarize_held_origin(rows)
    assert result["yellow"]["best_hold"]["duration_s"] >= 1.0
    assert result["yellow"]["best_motion"] is None
    assert result["red"]["best_motion"]["displacement_px"] > 35


def test_rejects_unknown_side():
    import pytest
    with pytest.raises(ValueError):
        central_cap_candidates([], "unknown")
