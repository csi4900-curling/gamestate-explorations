from copy import deepcopy
import json
from pathlib import Path

import pytest

from prototype.positive_patch_source_enrichment import attach_positive_source_reviews


BASE = Path(__file__).resolve().parents[2] / "validation/throw-event-benchmark/canada-latvia-2024"


def inputs():
    ledger = json.loads((BASE /
        "full-match-area-censored-candidate-handoff-all-negative-reviewed-development.json").read_text())
    audit = json.loads((BASE / "all-positive-patch-source-audit/manifest.json").read_text())
    return ledger, audit


def test_all_accepted_left_pixels_reviewed_without_physical_promotion():
    ledger, audit = inputs()
    result = attach_positive_source_reviews(ledger, audit)
    assert result["source_pixel_reviewed_accepted_left_count"] == 72
    assert result["accepted_left_source_pixel_class_counts"] == {
        "stone_shaped_pixels": 70, "person_pixels": 1, "ambiguous_pixels": 1}
    assert result["positive_postscore_source_reviewed_left_count"] == 38
    assert result["candidate_count"] == 147
    assert result["development_possible_event_review_count"] == 96
    assert result["physical_throw_count_verified"] is None
    assert result["complete_throw_sequence_verified"] is False
    assert all(row["physical_throw_verified"] is False and
               row["game_state_after"]["simulation_ready"] is False
               for row in result["ordered_candidates"])
    by_id = {row["candidate_id"]: row for row in result["ordered_candidates"]}
    assert by_id["left:R01-S32"]["source_pixel_review"]["source_pixel_class"] == "stone_body_pixels_in_crossing_crops"
    assert by_id["left:R01-S45"]["source_pixel_review"]["source_pixel_class"] == "person_at_crossing"
    assert by_id["left:R01-S119"]["source_pixel_review"]["source_pixel_class"].startswith("ambiguous")
    assert "postscore_source_review" not in ledger["ordered_candidates"][0]


def test_mismatched_score_or_pixel_class_cannot_join():
    ledger, audit = inputs()
    bad = deepcopy(audit)
    bad["rows"][0]["frozen_patch_mean_score"] += 1
    with pytest.raises(ValueError, match="cannot join"):
        attach_positive_source_reviews(ledger, bad)
    bad = deepcopy(audit)
    bad["rows"][0]["source_pixel_class"] = "person_head_pixels"
    with pytest.raises(ValueError, match="cannot join"):
        attach_positive_source_reviews(ledger, bad)
