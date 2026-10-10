import pytest

from shot_transition_confirmation import confirm_shot_transitions


def shot(shot_id, same, following):
    return {"shot_id": shot_id,
            "same_shot_candidates": [{"colour": colour} for colour in same],
            "following_shot_candidates": [{"colour": colour} for colour in following]}


def test_transition_needs_origin_prediction_and_matching_colour():
    predictions = [{"shot_id": "S01", "predicted": 1},
                   {"shot_id": "S02", "predicted": 1},
                   {"shot_id": "S03", "predicted": 0}]
    audits = {"cap": [shot("S01", ["yellow"], ["yellow"]),
                      shot("S02", ["red"], ["yellow"]),
                      shot("S03", ["red"], ["red"])]}
    decisions = confirm_shot_transitions(predictions, audits)
    assert [(row["status"], row["colour"]) for row in decisions] == [
        ("corroborated_candidate", "yellow"), ("unconfirmed", None),
        ("unconfirmed", "red")]


def test_second_channel_can_supply_motion_without_forcing_ambiguous_colour():
    predictions = [{"shot_id": "S01", "predicted": 1}]
    audits = {"cap": [shot("S01", ["yellow"], ["yellow"])],
              "learned": [shot("S01", ["red"], ["red"])]}
    decision = confirm_shot_transitions(predictions, audits)[0]
    assert decision["status"] == "corroborated_candidate"
    assert decision["colour"] is None
    assert decision["colour_status"] == "ambiguous"
    with pytest.raises(ValueError):
        confirm_shot_transitions(predictions, {"cap": []})
