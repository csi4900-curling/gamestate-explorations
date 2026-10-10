from copy import deepcopy

import pytest

from prototype.triage_split_partial_cap_deltas import triage_deltas


def fixtures():
    source = "a" * 64
    delta = {"source_sha256": source, "rows": [{
        "candidate_id": "left:L1", "comparison_status": "partial_cap_image_comparison",
        "image_cap_delta": {"no_longer_observed": ["C01"],
                            "newly_observed": ["C02"],
                            "unresolved_before": [], "unresolved_after": []},
    }]}
    context = {"source_sha256": source, "rows": [
        {"candidate_id": "left:L1", "phase": "pre",
         "local_observation_id": "C01", "colour": "red",
         "pixel_center": [400, 200], "context_tier": "clear_context_review"},
        {"candidate_id": "left:L1", "phase": "post",
         "local_observation_id": "C02", "colour": "yellow",
         "pixel_center": [450, 200], "context_tier": "clear_context_review"},
    ]}
    return delta, context


def test_clear_and_cluttered_image_changes_are_review_tiers_only():
    delta, context = fixtures()
    result = triage_deltas(delta, context)
    assert result["review_tier_counts"] == {"clear_context_change_review": 1}
    assert not result["rows"][0]["physical_transition_verified"]
    context = deepcopy(context)
    context["rows"][1]["context_tier"] = "context_cluttered_review"
    assert triage_deltas(delta, context)["rows"][0]["review_tier"] == (
        "cluttered_change_review")


def test_missing_changed_cap_context_is_rejected():
    delta, context = fixtures()
    context["rows"].pop()
    with pytest.raises(ValueError, match="Missing context"):
        triage_deltas(delta, context)


def test_window_abstention_remains_unknown():
    delta, context = fixtures()
    delta["rows"][0]["image_cap_delta"] = None
    delta["rows"][0]["comparison_status"] = "abstain_cross_window_scene_change"
    assert triage_deltas(delta, context)["rows"][0]["review_tier"] == (
        "window_or_scene_abstention")
