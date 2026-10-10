import pytest

from prototype.full_match_right_review_audit import audit


def fixtures():
    inventory = {"rows": [
        {"proposal_id": "R1:A", "temporal_status": "no_left_time_colour_candidate"},
        {"proposal_id": "R1:B", "temporal_status": "one_left_time_colour_candidate"},
        {"proposal_id": "R1:C", "temporal_status": "one_left_time_colour_candidate"}],
        "left_events_without_any_right_time_colour_candidate": ["L1"]}
    context = {"rows": [
        {"proposal_id": "R1:A", "context_tier": "context_cluttered_review"},
        {"proposal_id": "R1:B", "context_tier": "context_cluttered_review"},
        {"proposal_id": "R1:C", "context_tier": "clear_context_review"}]}
    right = [("R1", {"rows": [{"raw_track_id": "A",
                                "source_prefix_class": "person_or_wheelchair_or_equipment"}]})]
    left = {"rows": [{"left_event_id": "L1",
                      "source_prefix_class": "moving_broom_or_equipment"}]}
    matched = {"rows": [{"proposal_id": "R1:B",
                         "source_prefix_class": "person_or_wheelchair_or_equipment"}]}
    sample = {"rows": [{"proposal_id": "R1:C",
                        "source_prefix_class": "moving_stone"}]}
    return inventory, context, right, left, matched, sample


def test_audit_conserves_all_reviewed_disagreements():
    result = audit(*fixtures())
    assert result["right_only_source_class_counts"] == {
        "person_or_wheelchair_or_equipment": 1}
    assert result["matched_clear_sample_class_counts"] == {"moving_stone": 1}


def test_audit_rejects_missing_right_only_review():
    inputs = list(fixtures())
    inputs[2] = [("R1", {"rows": []})]
    with pytest.raises(ValueError, match="Every right temporal disagreement"):
        audit(*inputs)


def test_audit_accounts_for_duplicate_right_paths_separately():
    inputs = list(fixtures())
    inputs[0]["rows"].append({"proposal_id": "R1:D",
                              "temporal_status": "multiple_right_candidates_for_left_review"})
    inputs[1]["rows"].append({"proposal_id": "R1:D",
                              "context_tier": "clear_context_review"})
    inputs[2][0][1]["rows"].append({"raw_track_id": "D",
                                      "source_prefix_class": "moving_stone"})
    result = audit(*inputs)
    assert result["right_only_source_class_counts"] == {
        "person_or_wheelchair_or_equipment": 1}
    assert result["duplicate_right_source_class_counts"] == {"moving_stone": 1}
