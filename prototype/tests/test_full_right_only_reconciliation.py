from copy import deepcopy
import json
from pathlib import Path

import pytest

from prototype.full_right_only_reconciliation import reconcile_full_right_only


BASE = Path(__file__).resolve().parents[2] / "validation/throw-event-benchmark/canada-latvia-2024"


def inputs():
    ledger = json.loads((BASE /
        "full-match-area-censored-candidate-handoff-two-area-gap-recoveries-development.json").read_text())
    episodes = json.loads((BASE / "full-right-area-episodes-first-transfer.json").read_text())
    scan = json.loads((BASE / "full-right-area-first-transfer.json").read_text())
    audit = json.loads((BASE / "remaining-right-only-source-audit/manifest.json").read_text())
    return ledger, episodes, scan, audit


def test_all_frozen_right_only_proposals_accounted_without_event_promotion():
    ledger, episodes, scan, audit = inputs()
    result = reconcile_full_right_only(ledger, episodes, scan, audit)
    old = {row["candidate_id"]: row for row in ledger["ordered_candidates"]}
    new = {row["candidate_id"]: row for row in result["ordered_candidates"]}
    assert set(new) - set(old) == {
        "right_area:R01:A042", "right_area:R01:A182", "right_area:R01:A374"}
    assert all(new[key]["sequence_id"] == row["sequence_id"] for key, row in old.items())
    assert result["candidate_count"] == 152
    assert result["right_area_right_only_accounted_count"] == 32
    assert result["right_area_right_only_accounting_counts"] == {
        "existing_area_candidate": 22,
        "paired_older_right_entry_not_identity_proof": 7,
        "source_reviewed_nonstone_abstention_added": 3,
    }
    assert result["older_right_only_without_full_area_match"] == ["right:R008"]
    assert result["development_possible_event_review_count"] == 98
    assert result["physical_throw_count_verified"] is None
    assert result["complete_throw_sequence_verified"] is False
    assert all(row["physical_throw_verified"] is False and row[
        "game_state_after"]["simulation_ready"] is False for row in new.values())


def test_unreviewed_or_changed_right_only_path_cannot_disappear():
    ledger, episodes, scan, audit = inputs()
    bad = deepcopy(audit)
    bad["rows"] = bad["rows"][:-1]
    with pytest.raises(ValueError, match="inputs differ"):
        reconcile_full_right_only(ledger, episodes, scan, bad)
    bad = deepcopy(audit)
    bad["rows"][0]["observed_track_points"][0]["pixel"][0] += 1
    with pytest.raises(ValueError, match="lacks review"):
        reconcile_full_right_only(ledger, episodes, scan, bad)
