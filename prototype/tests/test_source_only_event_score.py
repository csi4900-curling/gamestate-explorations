import pytest

from prototype.scripts.score_source_only_event_windows import score, with_colour_hypotheses


def test_one_to_one_matching_reroutes_overlap_and_excludes_uncertain_boundary():
    review = {
        "source_sha256": "same",
        "independent_validation": False,
        "sampled_intervals_seconds": [[0, 100]],
        "uncertain_boundary_events": [{"interval_seconds": [0, 10]}],
        "events": [
            {"id": "A", "status": "clear", "delivery_interval_seconds": [20, 30], "colour": "red"},
            {"id": "B", "status": "clear", "delivery_interval_seconds": [40, 50], "colour": "yellow"},
        ],
    }
    ledger = {
        "source_sha256": "same",
        "events": [
            {"candidate_id": "excluded", "observation_anchor_s": 5, "release_window_s": [0, 8], "colour": "red"},
            {"candidate_id": "shared", "observation_anchor_s": 25, "release_window_s": [25, 45], "colour": "red"},
            {"candidate_id": "only_a", "observation_anchor_s": 26, "release_window_s": [26, 27], "colour": "red"},
        ],
    }
    result = score(review, ledger)
    assert result["eligible_candidates"] == 2
    assert result["temporal_true_positives"] == 2
    assert result["colour_aware_true_positives"] == 1
    assert result["unmatched_candidate_ids"] == []
    assert {item["label_id"]: item["candidate_id"] for item in result["matches"]} == {
        "A": "only_a", "B": "shared"
    }


def test_colour_hypothesis_is_versioned_and_cannot_override_counter():
    ledger = {"source_sha256": "source", "events": [
        {"candidate_id": "T1", "counter_id": None, "colour": "red"},
        {"candidate_id": "T2", "counter_id": "B1", "colour": "yellow"},
    ]}
    audit = {"source_sha256": "source", "ledger_sha256": "ledger", "rows": [
        {"candidate_id": "T1", "earliest_following_colour_hypothesis": "yellow"},
    ]}
    variant, applied = with_colour_hypotheses(ledger, audit, "ledger")
    assert ledger["events"][0]["colour"] == "red"
    assert variant["events"][0]["colour"] == "yellow"
    assert applied == [{"candidate_id": "T1", "ledger_colour": "red",
                        "hypothesis_colour": "yellow"}]
    audit["rows"].append({"candidate_id": "T2",
                          "earliest_following_colour_hypothesis": "red"})
    with pytest.raises(ValueError, match="counter-backed"):
        with_colour_hypotheses(ledger, audit, "ledger")


def test_candidate_starting_in_uncertain_edge_counts_if_window_reaches_clear_span():
    review = {
        "source_sha256": "same", "independent_validation": False,
        "sampled_intervals_seconds": [[0, 100]],
        "uncertain_boundary_events": [{"interval_seconds": [0, 10]}],
        "events": [{"id": "A", "status": "clear",
                    "delivery_interval_seconds": [10, 20], "colour": "red"}],
    }
    ledger = {"source_sha256": "same", "events": [
        {"candidate_id": "T1", "observation_anchor_s": 8,
         "release_window_s": [8, 15], "colour": "red"},
    ]}
    result = score(review, ledger)
    assert result["eligible_candidates"] == 1
    assert result["temporal_true_positives"] == 1
