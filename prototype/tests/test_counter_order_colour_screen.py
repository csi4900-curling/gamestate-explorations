import pytest

from counter_order_colour_screen import screen_order_proposals


def test_conflicting_and_unknown_source_colour_never_auto_link():
    proposals = [
        {"counter_id": "B80", "counter_colour": "red", "proposed_shot_id": "S372"},
        {"counter_id": "B86", "counter_colour": "red", "proposed_shot_id": "S411"},
    ]
    cues = [
        {
            "shot_id": "S372",
            "postcut_colour": None,
            "postcut_status": "ambiguous_or_absent_postcut_motion",
        },
        {
            "shot_id": "S411",
            "postcut_colour": "yellow",
            "postcut_status": "unique_strict_postcut_motion",
        },
    ]
    result = screen_order_proposals(proposals, cues)
    assert [row["screen_status"] for row in result] == [
        "visual_colour_abstained",
        "visual_colour_conflict",
    ]
    assert all(not row["safe_to_auto_link"] for row in result)


def test_even_matching_postcut_colour_is_not_identity_proof():
    result = screen_order_proposals(
        [{"counter_id": "B01", "counter_colour": "red", "proposed_shot_id": "S10"}],
        [
            {
                "shot_id": "S10",
                "postcut_colour": "red",
                "postcut_status": "unique_strict_postcut_motion",
            }
        ],
    )
    assert result[0]["screen_status"] == "colour_compatible_identity_unverified"
    assert result[0]["safe_to_auto_link"] is False


def test_duplicate_postcut_shot_rejected():
    with pytest.raises(ValueError, match="Duplicate"):
        screen_order_proposals([], [{"shot_id": "S10"}, {"shot_id": "S10"}])
