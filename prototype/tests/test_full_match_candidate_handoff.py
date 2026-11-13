import copy
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from full_match_candidate_handoff import build_full_match_candidate_handoff

BASE = ROOT / "validation/throw-event-benchmark/layout-router/full-2024-coverage/latvia24-full-v1"


def inputs():
    return [
        json.loads((BASE / name).read_text())
        for name in (
            "timeline.json",
            "run-02/events.json",
            "right-entry-variant-235-225.json",
            "right-entry-camera-aware-fusion.json",
            "right-entry-partial-cap-sequence-alignment-gated.json",
            "source-activity-coverage-overlay.json",
        )
    ]


def test_full_match_handoff_keeps_all_raw_and_right_observations():
    result = build_full_match_candidate_handoff(*inputs())
    assert result["candidate_counts_by_kind"] == {
        "left_provisional_passage": 72,
        "left_unconfirmed_raw_motion": 47,
        "right_only_review_entry": 8,
    }
    assert result["candidate_count"] == 127
    assert result["possible_event_proposal_count"] == 80
    assert all(
        not row["physical_throw_verified"] and not row["game_state_after"]["simulation_ready"]
        for row in result["ordered_candidates"]
    )
    right = [
        r
        for r in result["ordered_candidates"]
        if r["observation_kind"] == "right_only_review_entry"
    ]
    assert all(
        r["left_coverage_status"] == "left_static_right_active"
        and r["post_candidate_partial_board"]["complete_board_verified"] is False
        for r in right
    )
    assert [r["source_time_s"] for r in result["ordered_candidates"]] == sorted(
        r["source_time_s"] for r in result["ordered_candidates"]
    )


def test_rejects_right_colour_or_time_mismatch():
    args = inputs()
    changed = copy.deepcopy(args)
    changed[3]["right_entries"][0]["right_colour_claim"] = "red"
    with pytest.raises(ValueError, match="Right-only passage"):
        build_full_match_candidate_handoff(*changed)
    changed = copy.deepcopy(args)
    changed[4]["entries"][0]["entry_time_s"] += 1
    with pytest.raises(ValueError, match="Right-only passage"):
        build_full_match_candidate_handoff(*changed)


def test_rejects_left_motion_inside_blind_interval():
    args = inputs()
    changed = copy.deepcopy(args)
    changed[0]["observed_events"][0]["crossing_time_s"] = 5100
    changed[1]["events"][0]["crossing_time_s"] = 5100
    with pytest.raises(ValueError, match="Left motion candidate inside static-left"):
        build_full_match_candidate_handoff(*changed)


def test_source_pixel_review_flags_person_without_promoting_or_dropping_row():
    reviews = json.loads((BASE / "source-pixel-review-ledger.json").read_text())
    result = build_full_match_candidate_handoff(*inputs(), reviews)
    by_id = {r["candidate_id"]: r for r in result["ordered_candidates"]}
    assert result["candidate_count"] == 127
    assert result["source_pixel_review_counts"]["person_at_crossing"] == 1
    assert (
        by_id["left:R01-S45"]["source_pixel_review"]["source_pixel_class"] == "person_at_crossing"
    )
    assert by_id["left:R01-S45"]["observation_kind"] == "left_provisional_passage"
    assert not by_id["left:R01-S45"]["physical_throw_verified"]
    changed = copy.deepcopy(reviews)
    changed["reviews"][0]["colour_claim"] = "red"
    with pytest.raises(ValueError, match="Source-pixel review candidate differs"):
        build_full_match_candidate_handoff(*inputs(), changed)
