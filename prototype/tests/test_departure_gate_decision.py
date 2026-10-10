"""An early line yields a provisional colour and abstains on ties."""

from departure_gate_decision import decide_gate_colour


def row(red, yellow, red_tracks=(), yellow_tracks=()):
    return {"gate_counts": {"red": red, "yellow": yellow},
            "transits": {"red": list(red_tracks), "yellow": list(yellow_tracks)},
            "samples": [{"time_s": 1.0, "gate_candidates": {
                "red": [{"patch_score": 0.2}] * red,
                "yellow": [{"patch_score": 0.3}] * yellow}}]}


def test_coherent_transit_takes_priority_over_other_colour_count():
    t = {"point_count": 4, "displacement_px": 80, "interval_s": [2.0, 2.6]}
    decision = decide_gate_colour(row(6, 4, yellow_tracks=[t]))
    assert decision == {"colour": "yellow", "route": "coherent_early_gate_transit",
                        "anchor_s": 2.0}


def test_single_high_score_sample_can_supply_colour():
    decision = decide_gate_colour(row(0, 1))
    assert decision["colour"] == "yellow"
    assert decision["anchor_s"] == 1.0


def test_tied_counts_abstain():
    assert decide_gate_colour(row(2, 2))["colour"] is None
