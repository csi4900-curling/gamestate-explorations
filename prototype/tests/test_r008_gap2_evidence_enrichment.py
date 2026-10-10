from copy import deepcopy
import json
from pathlib import Path

import pytest

from prototype.r008_gap2_evidence_enrichment import attach_r008_gap2_evidence


BASE = Path(__file__).resolve().parents[2] / "validation/throw-event-benchmark/canada-latvia-2024"


def inputs():
    ledger = json.loads((BASE /
        "full-match-area-censored-candidate-handoff-all-area-right-only-accounted-development.json").read_text())
    audit = json.loads((BASE / "r008-area-gap2-split-audit.json").read_text())
    return ledger, audit


def test_r008_source_class_and_exact_gap2_match_do_not_promote_event():
    ledger, audit = inputs()
    result = attach_r008_gap2_evidence(ledger, audit)
    old = {row["candidate_id"]: row for row in ledger["ordered_candidates"]}
    new = {row["candidate_id"]: row for row in result["ordered_candidates"]}
    assert set(new) == set(old)
    assert old["right:R008"]["source_pixel_review"] is None
    assert new["right:R008"]["source_pixel_review"]["source_pixel_class"] == "moving_red_stone_body_pixels"
    assert new["right:R008"]["right_area_association_diagnostic"][
        "one_second_gap_raw_track_ids"] == ["A352", "A353"]
    assert result["candidate_count"] == 152
    assert result["development_possible_event_review_count"] == 98
    assert result["physical_throw_count_verified"] is None
    assert all(row["physical_throw_verified"] is False and row[
        "game_state_after"]["simulation_ready"] is False for row in new.values())


def test_r008_mismatched_diagnostic_cannot_join():
    ledger, audit = inputs()
    bad = deepcopy(audit)
    bad["old_prefix_equals_combined_split_raw_points"] = False
    with pytest.raises(ValueError, match="differ"):
        attach_r008_gap2_evidence(ledger, bad)
    bad = deepcopy(ledger)
    next(row for row in bad["ordered_candidates"] if row[
        "candidate_id"] == "right:R008")["source_pixel_review"] = {
            "source_pixel_class": "person_pixels"}
    with pytest.raises(ValueError, match="prior evidence differs"):
        attach_r008_gap2_evidence(bad, audit)
