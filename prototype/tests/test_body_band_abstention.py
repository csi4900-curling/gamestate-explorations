"""Check that the development gate only withholds covered frozen acceptances."""

import pytest

from body_band_abstention import apply_body_band_abstention


def test_only_low_supported_acceptance_becomes_abstention():
    screen = {
        "decisions": [
            {"candidate_id": "S1", "accepted": True, "status": "supported"},
            {"candidate_id": "S2", "accepted": True, "status": "supported"},
            {"candidate_id": "S3", "accepted": False, "status": "no_path"},
        ],
        "events": [{"id": "S1"}, {"id": "S2"}],
    }
    features = {"rows": [
        {"candidate_id": "S1", "max_neutral_gray_fraction": 0.49},
        {"candidate_id": "S2", "max_neutral_gray_fraction": 0.50},
    ]}
    result = apply_body_band_abstention(screen, features)
    assert result["flagged_candidate_ids"] == ["S1"]
    assert [row["id"] for row in result["events"]] == ["S2"]
    assert result["decisions"][0]["status"] == "abstain_low_neutral_stone_body_support"
    assert result["decisions"][2] == screen["decisions"][2]
    assert screen["decisions"][0]["accepted"] is True


def test_missing_or_duplicate_feature_coverage_is_rejected():
    screen = {"decisions": [{"candidate_id": "S1", "accepted": True}],
              "events": [{"id": "S1"}]}
    for rows in ([], [{"candidate_id": "S1"}, {"candidate_id": "S1"}]):
        with pytest.raises(ValueError):
            apply_body_band_abstention(screen, {"rows": rows})
