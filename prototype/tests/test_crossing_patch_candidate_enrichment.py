from copy import deepcopy
import json
from pathlib import Path

import pytest

from prototype.crossing_patch_candidate_enrichment import enrich_full_match_candidates


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation"


def inputs():
    union = json.loads(
        (
            BASE / "throw-event-benchmark/canada-latvia-2024/"
            "full-match-area-censored-candidate-handoff-development.json"
        ).read_text()
    )
    score = json.loads(
        (
            BASE / "official-shot-sequence/"
            "latvia-italy-frozen-crossing-patch-source-class-score.json"
        ).read_text()
    )
    packet = json.loads(
        (
            BASE / "official-shot-sequence/"
            "latvia-italy-crossing-patch-source-class-packet/manifest.json"
        ).read_text()
    )
    return union, score, packet


def test_graded_scores_preserve_event_and_game_state_claims():
    union, score, packet = inputs()
    enriched = enrich_full_match_candidates(union, score, packet)
    assert enriched["candidate_count"] == 147
    assert enriched["crossing_patch_scored_left_count"] == 13
    assert (
        enriched["development_possible_event_review_count"]
        == union["development_possible_event_review_count"]
    )
    assert enriched["physical_throw_count_verified"] is None
    assert enriched["complete_throw_sequence_verified"] is False
    assert all(
        row["physical_throw_verified"] is False
        and row["game_state_after"]["simulation_ready"] is False
        for row in enriched["ordered_candidates"]
    )
    by_id = {row["candidate_id"]: row for row in enriched["ordered_candidates"]}
    assert by_id["left:R01-S45"]["crossing_patch_appearance"]["model_positive"] is False
    assert by_id["left:R01-S35"]["crossing_patch_appearance"]["model_positive"] is False
    assert by_id["left:R01-S49"]["crossing_patch_appearance"]["model_positive"] is False
    assert "crossing_patch_appearance" not in by_id["left:R01-S76"]
    assert "crossing_patch_appearance" not in union["ordered_candidates"][0]


def test_score_cannot_join_wrong_source_or_reviewed_class():
    union, score, packet = inputs()
    bad = deepcopy(packet)
    source = next(row for row in bad["sources"] if row["source_id"] == union["source_id"])
    source["video_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="source differs"):
        enrich_full_match_candidates(union, score, bad)
    bad_score = deepcopy(score)
    person = next(row for row in bad_score["rows"] if row["event_id"] == "R01-S45")
    person["source_pixel_class"] = "stone_shaped_pixels"
    with pytest.raises(ValueError, match="score and source packet differ"):
        enrich_full_match_candidates(union, bad_score, packet)


def test_all_accepted_scores_keep_unknown_reviews_unknown():
    union, _, _ = inputs()
    base = BASE / "throw-event-benchmark/canada-latvia-2024"
    score = json.loads(
        (base / "all-accepted-left-crossing-patch-score-development.json").read_text()
    )
    packet = json.loads(
        (base / "all-accepted-left-crossing-patch-packet/manifest.json").read_text()
    )
    enriched = enrich_full_match_candidates(union, score, packet)
    assert enriched["crossing_patch_scored_left_count"] == 72
    assert enriched["candidate_count"] == 147
    assert enriched["development_possible_event_review_count"] == 96
    assert enriched["physical_throw_count_verified"] is None
    by_id = {row["candidate_id"]: row for row in enriched["ordered_candidates"]}
    assert by_id["left:R01-S05"]["source_pixel_review"] is None
    assert (
        by_id["left:R01-S05"]["crossing_patch_appearance"]["source_review_status"] == "unreviewed"
    )
    assert by_id["left:R01-S35"]["crossing_patch_appearance"]["model_positive"] is False
    assert (
        by_id["left:R01-S119"]["crossing_patch_appearance"]["source_review_status"]
        == "ambiguous_pixels"
    )
    assert "crossing_patch_appearance" not in by_id["left:R01-S76"]
    assert all(
        row["game_state_after"]["simulation_ready"] is False
        for row in enriched["ordered_candidates"]
    )


def test_postscore_source_reviews_attach_without_rewriting_score_origin():
    union, _, _ = inputs()
    base = BASE / "throw-event-benchmark/canada-latvia-2024"
    score = json.loads(
        (base / "all-accepted-left-crossing-patch-score-development.json").read_text()
    )
    packet = json.loads(
        (base / "all-accepted-left-crossing-patch-packet/manifest.json").read_text()
    )
    audit = json.loads((base / "lowest-five-patch-source-audit/manifest.json").read_text())
    enriched = enrich_full_match_candidates(union, score, packet, audit)
    assert enriched["postscore_source_reviewed_left_count"] == 5
    by_id = {row["candidate_id"]: row for row in enriched["ordered_candidates"]}
    for event_id in ("S15", "S05", "S105", "S13", "S54"):
        row = by_id["left:R01-" + event_id]
        assert "stone_body" in row["source_pixel_review"]["source_pixel_class"]
        assert row["crossing_patch_appearance"]["source_review_status"] == "unreviewed"
        assert row["crossing_patch_appearance"]["source_review_added_after_scoring"] is True
        assert row["physical_throw_verified"] is False
    bad = deepcopy(audit)
    bad["rows"][0]["frozen_patch_mean_score"] += 1
    with pytest.raises(ValueError, match="cannot join"):
        enrich_full_match_candidates(union, score, packet, bad)


def test_all_negative_review_keeps_prior_classes_and_marks_new_reviews():
    union, _, _ = inputs()
    base = BASE / "throw-event-benchmark/canada-latvia-2024"
    score = json.loads(
        (base / "all-accepted-left-crossing-patch-score-development.json").read_text()
    )
    packet = json.loads(
        (base / "all-accepted-left-crossing-patch-packet/manifest.json").read_text()
    )
    audit = json.loads((base / "all-negative-patch-source-audit/manifest.json").read_text())
    enriched = enrich_full_match_candidates(union, score, packet, audit)
    assert enriched["postscore_source_reviewed_left_count"] == 34
    by_id = {row["candidate_id"]: row for row in enriched["ordered_candidates"]}
    assert (
        by_id["left:R01-S45"]["source_pixel_review"]["source_pixel_class"] == "person_at_crossing"
    )
    assert by_id["left:R01-S119"]["source_pixel_review"]["source_pixel_class"].startswith(
        "ambiguous"
    )
    assert (
        by_id["left:R01-S15"]["source_pixel_review"]["source_pixel_class"]
        == "stone_body_pixels_in_crossing_crops"
    )
    assert (
        by_id["left:R01-S15"]["crossing_patch_appearance"]["source_review_status"] == "unreviewed"
    )
    assert sum("postscore_source_review" in row for row in enriched["ordered_candidates"]) == 34
    assert enriched["development_possible_event_review_count"] == 96
    assert enriched["physical_throw_count_verified"] is None
