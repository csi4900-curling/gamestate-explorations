import pytest

from counter_sequence_order import audit_counter_sequence_order


def row(counter, shot=None, options=()):
    return {"counter_id": counter, "colour": "red", "shot_id": shot,
            "candidate_shots": [{"shot_id": item[0],
                                 "origin_probability": item[1]}
                                for item in options]}


def test_unique_option_between_neighbouring_links():
    audit = audit_counter_sequence_order([
        row("B01", "S10"), row("B02", options=(("S12", 0.8), ("S21", 0.9))),
        row("B03", "S20")])
    proposal = audit["multi_option_counter_proposals"][0]
    assert proposal["proposed_shot_id"] == "S12"
    assert [option["passes_order_and_origin"] for option in proposal["options"]] == [
        True, False]


def test_conflicting_anchors_force_abstention_and_are_reported():
    audit = audit_counter_sequence_order([
        row("B01", "S20"), row("B02", options=(("S12", 0.9),
                                                  ("S25", 0.9))),
        row("B03", "S10")])
    assert len(audit["anchor_reversals"]) == 1
    proposal = audit["multi_option_counter_proposals"][0]
    assert proposal["contradictory_anchors"]
    assert proposal["proposed_shot_id"] is None


def test_two_in_order_options_abstain_and_duplicate_option_rejected():
    audit = audit_counter_sequence_order([
        row("B01", "S10"), row("B02", options=(("S12", 0.8),
                                                  ("S13", 0.9))),
        row("B03", "S20")])
    assert audit["multi_option_counter_proposals"][0]["proposed_shot_id"] is None
    with pytest.raises(ValueError, match="Duplicate option"):
        audit_counter_sequence_order([
            row("B01", "S10"), row("B02", options=(("S12", 0.8),
                                                      ("S12", 0.9)))])
