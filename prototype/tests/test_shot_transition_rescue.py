import pytest

from shot_transition_rescue import rescue_weak_origins


def decision(shot_id, cap, learned, status="unconfirmed"):
    return {
        "shot_id": shot_id,
        "status": status,
        "reason": "shot_origin_not_predicted",
        "channel_support": [
            *({"channel": "cap", "colour": colour} for colour in cap),
            *({"channel": "learned", "colour": colour} for colour in learned),
        ],
    }


def test_rescue_requires_probability_phase_and_unique_cross_channel_colour():
    origins = [
        {"shot_id": "S01", "predicted": 0, "phase_supported": True, "probability": 0.26},
        {"shot_id": "S02", "predicted": 0, "phase_supported": True, "probability": 0.1},
        {"shot_id": "S03", "predicted": 0, "phase_supported": False, "probability": 0.8},
    ]
    decisions = [
        decision("S01", ["red"], ["red", "yellow"]),
        decision("S02", ["red"], ["red"]),
        decision("S03", ["red"], ["red"]),
    ]
    result = rescue_weak_origins(origins, decisions)
    assert [row["status"] for row in result] == ["rescued_candidate", "unconfirmed", "unconfirmed"]
    assert result[0]["rescued_colour"] == "red"


def test_conflicting_or_ambiguous_channels_cannot_rescue():
    origin = [{"shot_id": "S01", "predicted": 0, "phase_supported": True, "probability": 0.5}]
    assert (
        rescue_weak_origins(origin, [decision("S01", ["red"], ["yellow"])])[0]["status"]
        == "unconfirmed"
    )
    assert (
        rescue_weak_origins(origin, [decision("S01", ["red", "yellow"], ["red", "yellow"])])[0][
            "status"
        ]
        == "unconfirmed"
    )
    with pytest.raises(ValueError):
        rescue_weak_origins(origin, [])
