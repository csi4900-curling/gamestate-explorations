"""Orientation persists through quiet shots but changes on clear motion."""

from dual_departure_gate import route_gate_sides


def gate(count, colour="red", points=0):
    return {
        "gate_counts": {
            "red": count if colour == "red" else 0,
            "yellow": count if colour == "yellow" else 0,
        },
        "transits": {
            "red": [{"point_count": points, "displacement_px": 80, "interval_s": [1, 2]}]
            if points and colour == "red"
            else [],
            "yellow": [{"point_count": points, "displacement_px": 80, "interval_s": [1, 2]}]
            if points and colour == "yellow"
            else [],
        },
        "samples": [
            {
                "time_s": 1.0,
                "gate_candidates": {
                    "red": [{"patch_score": 0.2}] * (count if colour == "red" else 0),
                    "yellow": [{"patch_score": 0.2}] * (count if colour == "yellow" else 0),
                },
            }
        ],
    }


def pair(identifier, left, right):
    return {"shot_id": identifier, "interval_s": [0, 10], "left": left, "right": right}


def test_motion_switches_side_and_quiet_shot_carries_it():
    rows = [
        pair("S1", gate(6, points=5), gate(0)),
        pair("S2", gate(20), gate(3, colour="yellow")),
        pair("S3", gate(0), gate(4, colour="yellow", points=4)),
    ]
    routed = route_gate_sides(rows)
    assert [row["side"] for row in routed] == ["left", "left", "right"]
    assert routed[1]["side_route"] == "carried_motion_selected_side"
    assert routed[2]["colour"] == "yellow"


def test_no_orientation_evidence_abstains():
    (row,) = route_gate_sides([pair("S1", gate(0), gate(0))])
    assert row["side"] is None
    assert row["colour"] is None
