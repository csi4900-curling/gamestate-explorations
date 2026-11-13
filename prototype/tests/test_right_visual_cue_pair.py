import pytest

from right_visual_cue_pair import group_visual_priority, visual_cue_pair


def test_two_frozen_cues_have_review_tiers_not_event_decisions():
    assert visual_cue_pair("clear_context_review", True) == ("both_visual_cues_positive_review")
    assert visual_cue_pair("clear_context_review", False) == ("visual_cues_disagree_review")
    assert visual_cue_pair("context_cluttered_review", True) == ("visual_cues_disagree_review")
    assert visual_cue_pair("context_cluttered_review", False) == ("both_visual_cues_weak_review")
    assert visual_cue_pair("context_unavailable_review", False) == ("context_unavailable_review")


def test_group_priority_retains_disagreement_and_weak_cases():
    assert group_visual_priority(["both_visual_cues_weak_review"] * 2) == (
        "all_visual_cues_weak_review"
    )
    assert group_visual_priority(
        ["both_visual_cues_weak_review", "visual_cues_disagree_review"]
    ) == ("contains_visual_cue_disagreement")
    assert group_visual_priority(
        ["both_visual_cues_positive_review", "both_visual_cues_weak_review"]
    ) == ("contains_both_visual_cues_positive")
    with pytest.raises(ValueError):
        group_visual_priority([])
