import pytest

from blind_throw_scoring import score_throw_intervals
from scripts.score_blind_throw_interval import validate_labels


def reference(id_, start, end, *, uncertain=False, colour="red"):
    return {"id": id_, "delivery_source_interval_s": [start, end],
            "uncertain": uncertain, "colour": colour}


def prediction(id_, time, colour="red"):
    return {"id": id_, "crossing_time_s": time, "colour": colour}


def test_duplicate_proposal_is_false_positive_and_miss_is_false_negative():
    result = score_throw_intervals(
        [reference("E1", 1, 4), reference("E2", 8, 11)],
        [prediction("S1", 2), prediction("S2", 3)])
    assert (result["true_positive_certain"], result["false_positive_outside_uncertain_intervals"],
            result["false_negative_certain"]) == (1, 1, 1)
    assert result["f1"] == 0.5


def test_uncertain_delivery_quarantines_predictions_and_blocks_full_f1():
    result = score_throw_intervals(
        [reference("E1", 1, 4), reference("E2", 8, 11, uncertain=True)],
        [prediction("S1", 2), prediction("S2", 9), prediction("S3", 15)])
    assert result["f1"] is None
    assert result["quarantined_prediction_ids"] == ["S2"]
    assert result["unmatched_prediction_ids"] == ["S3"]


def test_zero_matches_scores_zero_and_touching_intervals_rejected():
    result = score_throw_intervals([reference("E1", 1, 4)], [prediction("S1", 5)])
    assert result["f1"] == 0.0
    with pytest.raises(ValueError):
        score_throw_intervals([reference("E1", 1, 4), reference("E2", 4, 6)], [])


def test_seal_requires_complete_coverage_and_explained_uncertainty():
    packet = {"video_sha256": "video", "source_offset_s": 10,
              "interval_local_s": [0, 120], "chunk_count": 2}
    draft = {"schema": "blind_throw_interval_v1", "source_sha256": "video",
             "source_offset_s": 10, "interval_local_s": [0, 120],
             "reviewer": "independent reviewer", "independent_confirmed": True,
             "reviewed_minutes": [True, False], "events": [
                 {"id": "E1", "delivery_local_interval_s": [1, 4],
                  "delivery_source_interval_s": [11, 14], "colour": "unknown",
                  "uncertain": True, "notes": ""}]}
    with pytest.raises(ValueError, match="Every minute"):
        validate_labels(draft, packet)
    draft["reviewed_minutes"][1] = True
    with pytest.raises(ValueError, match="Invalid delivery"):
        validate_labels(draft, packet)
    draft["events"][0]["notes"] = "Release obscured"
    validate_labels(draft, packet)
