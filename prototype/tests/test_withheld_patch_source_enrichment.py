from copy import deepcopy
import json
from pathlib import Path

import pytest

from prototype.withheld_patch_source_enrichment import attach_withheld_source_reviews


BASE = Path(__file__).resolve().parents[2] / "validation/throw-event-benchmark/canada-latvia-2024"


def inputs():
    ledger = json.loads((BASE /
        "full-match-area-censored-candidate-handoff-all-accepted-left-source-reviewed-development.json").read_text())
    audit = json.loads((BASE /
        "withheld-left-crossing-patch-source-audit/manifest.json").read_text())
    return ledger, audit


def test_all_withheld_pixels_reviewed_without_event_or_state_promotion():
    ledger, audit = inputs()
    result = attach_withheld_source_reviews(ledger, audit)
    assert result["source_pixel_reviewed_withheld_left_count"] == 47
    assert result["withheld_left_source_pixel_class_counts"] == {
        "person_or_equipment_pixels_in_crossing_crops": 45,
        "ambiguous_low_red_pixels_near_wheelchair": 2,
    }
    assert result["source_pixel_reviewed_accepted_left_count"] == 72
    assert result["candidate_count"] == 147
    assert result["development_possible_event_review_count"] == 96
    assert result["physical_throw_count_verified"] is None
    assert result["complete_throw_sequence_verified"] is False
    assert all(row["physical_throw_verified"] is False and
               row["game_state_after"]["simulation_ready"] is False
               for row in result["ordered_candidates"])
    by_id = {row["candidate_id"]: row for row in result["ordered_candidates"]}
    assert by_id["left:R01-S99"]["postscore_source_review"]["source_pixel_class"].startswith("ambiguous")
    assert by_id["left:R01-S44"]["postscore_source_review"]["source_pixel_class"].startswith("person")
    assert "postscore_source_review" not in next(row for row in ledger["ordered_candidates"]
        if row["candidate_id"] == "left:R01-S01")


def test_conflicting_prior_class_and_duplicate_review_cannot_join():
    ledger, audit = inputs()
    bad = deepcopy(audit)
    next(row for row in bad["rows"] if row["candidate_id"] == "R01-S10")[
        "source_pixel_class"] = "ambiguous_low_red_pixels_near_wheelchair"
    with pytest.raises(ValueError, match="conflicts"):
        attach_withheld_source_reviews(ledger, bad)
    bad = deepcopy(audit)
    bad["rows"][1] = deepcopy(bad["rows"][0])
    with pytest.raises(ValueError, match="cannot join"):
        attach_withheld_source_reviews(ledger, bad)
