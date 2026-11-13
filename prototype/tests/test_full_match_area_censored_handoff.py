from copy import deepcopy
import json
from pathlib import Path

import pytest

from prototype.full_match_area_censored_handoff import (
    build_full_match_area_censored_handoff,
)


BASE = Path(__file__).resolve().parents[2] / "validation/throw-event-benchmark"


def inputs():
    legacy = json.loads(
        (
            BASE / "layout-router/full-2024-coverage/latvia24-full-v1/"
            "full-match-candidate-partial-state-handoff.json"
        ).read_text()
    )
    late = json.loads(
        (BASE / "canada-latvia-2024/end6-censored-event-state-development.json").read_text()
    )
    audit = json.loads(
        (BASE / "canada-latvia-2024/withheld-cross-view-source-audit/manifest.json").read_text()
    )
    no_right = json.loads(
        (BASE / "canada-latvia-2024/accepted-no-right-source-audit/manifest.json").read_text()
    )
    return legacy, late, audit, no_right


def test_full_match_union_retains_abstentions_and_person_paths():
    legacy, late, audit, no_right = inputs()
    merged = build_full_match_area_censored_handoff(legacy, late, audit, no_right)
    assert merged["candidate_count"] == 147
    assert merged["candidate_counts_by_kind"] == {
        "left_unconfirmed_raw_motion": 47,
        "left_provisional_passage": 72,
        "right_only_review_entry": 8,
        "right_area_reviewed_stone_pixels": 16,
        "right_area_reviewed_person_pixels": 4,
    }
    assert merged["development_possible_event_review_count"] == 96
    assert merged["source_reviewed_withheld_cross_view_count"] == 8
    assert merged["source_reviewed_accepted_no_right_count"] == 10
    assert merged["physical_throw_count_verified"] is None
    assert merged["complete_throw_sequence_verified"] is False
    assert all(
        row["game_state_after"]["simulation_ready"] is False for row in merged["ordered_candidates"]
    )
    assert len({row["candidate_id"] for row in merged["ordered_candidates"]}) == 147
    assert [row["source_time_s"] for row in merged["ordered_candidates"]] == sorted(
        row["source_time_s"] for row in merged["ordered_candidates"]
    )
    s76 = next(row for row in merged["ordered_candidates"] if row["candidate_id"] == "left:R01-S76")
    assert s76["source_pixel_review"]["clearly_nonstone_at_marked_pixel"]
    assert s76["withheld_cross_view_review"]["physical_throw_promotion"] is False
    s04 = next(row for row in merged["ordered_candidates"] if row["candidate_id"] == "left:R01-S04")
    assert s04["accepted_no_right_source_review"]["stone_shaped_pixels_at_crossing"] is True


def test_duplicate_time_or_source_mismatch_cannot_inflate_event_reviews():
    legacy, late, audit, no_right = inputs()
    bad = deepcopy(late)
    bad["source_video_sha256"]["lowres"] = "0" * 64
    with pytest.raises(ValueError, match="fingerprints"):
        build_full_match_area_censored_handoff(legacy, bad, audit, no_right)
    bad = deepcopy(late)
    existing = next(
        row
        for row in legacy["ordered_candidates"]
        if row["observation_kind"] == "right_only_review_entry"
    )
    bad["events"][0]["passage_time_s"] = existing["source_time_s"]
    with pytest.raises(ValueError, match="duplicated"):
        build_full_match_area_censored_handoff(legacy, bad, audit, no_right)
    bad_audit = deepcopy(audit)
    left = next(row for row in bad_audit["marked_pixels"] if row["candidate_id"] == "S76")
    left["source_time_s"] += 1
    with pytest.raises(ValueError, match="Withheld left source review"):
        build_full_match_area_censored_handoff(legacy, late, bad_audit, no_right)
    bad_no_right = deepcopy(no_right)
    bad_no_right["rows"][0]["right_time_colour_direction_candidate_count"] = 1
    with pytest.raises(ValueError, match="Accepted no-right source review"):
        build_full_match_area_censored_handoff(legacy, late, audit, bad_no_right)
