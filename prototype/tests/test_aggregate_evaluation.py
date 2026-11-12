import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aggregate_evaluation import score_event_to_top_view


def event(key, usable):
    return {
        "candidate_id": key,
        "segments": [
            {
                "geometry_samples": [
                    {"top_view_m": [0, 0] if usable else None},
                    {"top_view_m": [0, 1] if usable else None},
                ]
            }
        ],
    }


def test_good_event_detection_can_have_zero_aggregate_recall():
    result = score_event_to_top_view(
        {"events": [event("a", False), event("b", False)]},
        [
            {"candidate_id": "a", "verdict": "TP", "official_shot_id": "one"},
            {"candidate_id": "b", "verdict": "FP", "official_shot_id": ""},
        ],
        1,
    )
    assert result["event_TP"] == 1
    assert result["end_to_end_trajectory_recall"] == 0
    assert result["end_to_end_trajectory_precision"] is None


def test_outputs_on_false_events_cannot_improve_aggregate_recall():
    result = score_event_to_top_view(
        {"events": [event("a", False), event("b", True)]},
        [
            {"candidate_id": "a", "verdict": "TP", "official_shot_id": "one"},
            {"candidate_id": "b", "verdict": "FP", "official_shot_id": ""},
        ],
        2,
    )
    assert result["top_view_output_recall_ceiling"] == 0
    assert result["true_throws_without_top_view_output"] == 2
    assert result["top_view_outputs_on_event_false_positives"] == 1


def test_missing_candidate_reviews_and_duplicate_official_matches_are_rejected():
    aggregate = {"events": [event("a", True), event("b", True)]}
    with pytest.raises(ValueError, match="Every candidate"):
        score_event_to_top_view(aggregate, [], 2)
    with pytest.raises(ValueError, match="one-to-one"):
        score_event_to_top_view(
            aggregate,
            [
                {"candidate_id": key, "verdict": "TP", "official_shot_id": "same"}
                for key in ("a", "b")
            ],
            2,
        )


def test_empty_official_identity_is_not_a_true_positive():
    with pytest.raises(ValueError, match="nonempty"):
        score_event_to_top_view(
            {"events": [event("a", False)]},
            [{"candidate_id": "a", "verdict": "TP", "official_shot_id": ""}],
            1,
        )


def test_checkpoint_review_rejects_missing_rows_wrong_times_and_nonboolean_labels():
    from copy import deepcopy
    from aggregate_evaluation import validate_checkpoint_review

    events = [
        {
            "candidate_id": "a",
            "event_prediction": {"observed_track_points": [{"time_s": t} for t in (1, 2, 3)]},
        }
    ]
    selection = [{"candidate_id": "a", "checkpoint_times_s": [1, 2, 3]}]
    labels = [{**selection[0], "stone_at_checkpoints": [True, True, False]}]
    validate_checkpoint_review(events, selection, labels)
    with pytest.raises(ValueError, match="exactly once"):
        validate_checkpoint_review(events, [], labels)
    with pytest.raises(ValueError, match="exactly once"):
        validate_checkpoint_review(events, selection * 2, labels)
    wrong = deepcopy(labels)
    wrong[0]["checkpoint_times_s"][1] = 9
    with pytest.raises(ValueError, match="timestamps"):
        validate_checkpoint_review(events, selection, wrong)
    wrong = deepcopy(labels)
    wrong[0]["stone_at_checkpoints"] = ["false"] * 3
    with pytest.raises(ValueError, match="boolean"):
        validate_checkpoint_review(events, selection, wrong)
