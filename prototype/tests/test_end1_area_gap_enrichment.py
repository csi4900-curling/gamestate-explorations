from copy import deepcopy
import json
from pathlib import Path

import pytest

from prototype.end1_area_gap_enrichment import attach_end1_area_gap_candidate


BASE = Path(__file__).resolve().parents[2] / "validation/throw-event-benchmark/canada-latvia-2024"


def inputs():
    ledger = json.loads(
        (BASE / "full-match-area-censored-candidate-handoff-end5-gap-development.json").read_text()
    )
    audit = json.loads((BASE / "end1-omitted-right-area-source-audit/manifest.json").read_text())
    scan = json.loads((BASE / "full-right-area-first-transfer.json").read_text())
    return ledger, audit, scan


def test_omitted_end1_path_added_without_relabelling_old_candidates():
    ledger, audit, scan = inputs()
    result = attach_end1_area_gap_candidate(ledger, audit, scan)
    old = {row["candidate_id"]: row for row in ledger["ordered_candidates"]}
    new = {row["candidate_id"]: row for row in result["ordered_candidates"]}
    assert set(new) == set(old) | {"right_area:R01:A008"}
    assert all(new[key]["sequence_id"] == row["sequence_id"] for key, row in old.items())
    assert [row["merged_order_index"] for row in result["ordered_candidates"]] == list(
        range(1, 150)
    )
    a008 = new["right_area:R01:A008"]
    assert (
        new["left:R01-S07"]["source_time_s"]
        < a008["source_time_s"]
        < new["left:R01-S11"]["source_time_s"]
    )
    assert a008["colour_claim"] == "red"
    assert len(a008["observed_motion"]["points"]) == 6
    assert a008["sequence_id"] == "P009a"
    assert a008["game_state_after"]["complete_board"] is None
    assert result["candidate_count"] == 149
    assert result["development_possible_event_review_count"] == 98
    assert result["physical_throw_count_verified"] is None
    assert result["complete_throw_sequence_verified"] is False
    assert all(
        row["physical_throw_verified"] is False
        and row["game_state_after"]["simulation_ready"] is False
        for row in new.values()
    )


def test_mismatched_path_or_overlapping_candidate_cannot_join():
    ledger, audit, scan = inputs()
    bad = deepcopy(audit)
    bad["observed_track_points"][0]["pixel"][0] += 1
    with pytest.raises(ValueError, match="frozen right-area proposal"):
        attach_end1_area_gap_candidate(ledger, bad, scan)
    bad = deepcopy(ledger)
    next(row for row in bad["ordered_candidates"] if row["candidate_id"] == "left:R01-S07")[
        "source_time_s"
    ] = audit["source_time_s"]
    with pytest.raises(ValueError, match="declared review gap"):
        attach_end1_area_gap_candidate(bad, audit, scan)
