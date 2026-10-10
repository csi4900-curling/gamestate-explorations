from copy import deepcopy

import pytest

from prototype.full_match_evidence_union import build_evidence_union


def fixture_inputs():
    return {
        "raw": {"source_sha256": "source", "source_id": "match", "events": [
            {"id": "S1", "crossing_time_s": 10, "colour": "red"},
            {"id": "S2", "crossing_time_s": 20, "colour": "yellow"},
            {"id": "S3", "crossing_time_s": 21, "colour": "yellow"}]},
        "screen": {"source_sha256": "source", "decisions": [
            {"candidate_id": "S1", "accepted": True, "status": "supported"},
            {"candidate_id": "S2", "accepted": False, "status": "ambiguous"},
            {"candidate_id": "S3", "accepted": False, "status": "ambiguous"}]},
        "sequence": {"source_sha256": "source", "source_id": "match",
                     "events": [{"candidate_id": "S1", "agent_source_review": None,
                                 "post_event_observation": {
                                     "status": "partial_stable_view_local_board",
                                     "stones": [{"colour": "red"}]}}]},
        "prefixes": {"proposals": [{
            "candidate_id": "S2", "prefix_samples": [{"source_time_s": 20.5}],
            "first_ambiguity_time_s": 21, "duplicate_candidate_ids": ["S3"]}]},
        "prefix_boards": {"source_sha256": "source", "rows": [
            {"candidate_id": "S2", "board": {
                "status": "partial_stable_view_local_board",
                "stones": [{"colour": "yellow"}]}}]},
        "right_links": {"source_sha256": "source", "links": [
            {"right_raw_track_id": "R1", "right_entry_time_s": 17,
             "right_colour_claim": "red",
             "match_status": "unique_conditional_time_colour_link",
             "left_candidate_id": "S1"}]},
        "right_review": {"source_sha256": "source", "review": [
            {"raw_track_id": "R1", "sampled_prefix_class": "moving_stone"}]},
    }


def test_conserves_raw_ids_and_separates_review_from_accepted_event():
    output = build_evidence_union(**fixture_inputs())
    assert output["candidate_tier_counts"] == {
        "screen_provisional": 1, "pre_split_review_only": 1,
        "duplicate_pre_split_trigger": 1}
    assert output["raw_trigger_count"] == 3
    assert output["partial_board_count"] == 2
    assert output["conditional_right_link_count"] == 1
    assert output["raw_candidates"][2]["duplicate_of_candidate_id"] == "S2"
    assert all(not row["simulation_ready"] for row in output["raw_candidates"])


def test_rejects_wrong_right_colour_and_mismatched_source():
    data = fixture_inputs()
    wrong_colour = deepcopy(data)
    wrong_colour["right_links"]["links"][0]["right_colour_claim"] = "yellow"
    with pytest.raises(ValueError, match="colour"):
        build_evidence_union(**wrong_colour)
    data["right_review"]["source_sha256"] = "other"
    with pytest.raises(ValueError, match="fingerprint"):
        build_evidence_union(**data)
