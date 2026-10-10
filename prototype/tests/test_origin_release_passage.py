from prototype.origin_release_passage import hold_to_motion_passages


def row(time_s, colour, x, y):
    return {"time_s": time_s, "colour": colour, "pixel": [x, y]}


def test_held_stone_then_motion_yields_one_release_cue():
    observations = [
        row(t, "yellow", 370 + (1 if index % 2 else 0), 300)
        for index, t in enumerate((10, 10.2, 10.4, 10.6, 10.8, 11.0, 11.2))
    ]
    observations += [
        row(11.4, "yellow", 382, 303),
        row(11.6, "yellow", 410, 310),
        row(11.8, "yellow", 450, 322),
    ]
    found = hold_to_motion_passages(observations)
    assert len(found) == 1
    assert found[0]["colour"] == "yellow"
    assert found[0]["release_cue_s"] == 11.4


def test_fast_motion_without_held_lead_in_abstains():
    observations = [
        row(10, "red", 370, 300),
        row(10.2, "red", 400, 310),
        row(10.4, "red", 440, 325),
    ]
    assert hold_to_motion_passages(observations) == []
