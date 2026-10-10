from nonorigin_continuity_rescue import rescue_nonorigin_shots


def track(colour, points=12, span=100, start=20):
    return {
        "colour": colour,
        "point_count": points,
        "span_px": span,
        "interval_s": [start, start + 2],
    }


def shot(shot_id, start, stop, tracks):
    return {"shot_id": shot_id, "interval_s": [start, stop], "same_shot_candidates": tracks}


def test_rescues_only_nonorigin_motion_continuing_across_cut():
    shots = [
        shot("A", 0, 10, []),
        shot("B", 45, 60, [track("red", start=52)]),
        shot("C", 60, 80, [track("red", start=60)]),
    ]
    origins = {
        "A": {"predicted": 1, "probability": 0.9},
        "B": {"predicted": 0, "probability": 0.27},
        "C": {"predicted": 0, "probability": 0.01},
    }
    result = rescue_nonorigin_shots(shots, origins, (0, 90))
    assert [(row["shot_id"], row["colour"], row["following_shot_id"]) for row in result] == [
        ("B", "red", "C")
    ]


def test_rejects_adjacent_duplicate_and_noncontinuing_motion():
    shots = [
        shot("A", 0, 10, []),
        shot("B", 10, 20, [track("red")]),
        shot("C", 20, 30, [track("red")]),
        shot("D", 60, 70, [track("yellow")]),
        shot("E", 70, 80, [track("red")]),
    ]
    origins = {
        "A": {"predicted": 1, "probability": 0.9},
        "B": {"predicted": 0, "probability": 0.27},
        "C": {"predicted": 0, "probability": 0.01},
        "D": {"predicted": 0, "probability": 0.27},
        "E": {"predicted": 0, "probability": 0.01},
    }
    assert rescue_nonorigin_shots(shots, origins, (0, 90)) == []


def test_competing_shared_colours_remain_ambiguous():
    shots = [
        shot("A", 0, 10, []),
        shot("B", 45, 60, [track("red"), track("yellow")]),
        shot("C", 60, 80, [track("red"), track("yellow")]),
    ]
    origins = {
        "A": {"predicted": 1, "probability": 0.9},
        "B": {"predicted": 0, "probability": 0.27},
        "C": {"predicted": 0, "probability": 0.01},
    }
    assert rescue_nonorigin_shots(shots, origins, (0, 90)) == []
