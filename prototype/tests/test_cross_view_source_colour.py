import pytest

from cross_view_source_colour import join_source_colour


def event(colour="yellow", ledger="red"):
    return {
        "event_id": "VISUAL-S10",
        "source_shot_ids": ["S10"],
        "counter_id": None,
        "ledger_colour": ledger,
        "unique_passage_colour": colour,
        "unique_release_cue_s": 12.4,
    }


def postcut(colour, status="unique_strict_postcut_motion"):
    return {"shot_id": "S10", "postcut_colour": colour, "postcut_status": status}


def test_two_source_colours_expose_ledger_conflict_without_identity_claim():
    row = join_source_colour([event()], [postcut("yellow")])[0]
    assert row["source_colour"] == "yellow"
    assert row["ledger_relation"] == "conflicts_with_ledger"
    assert row["physical_stone_identity_verified"] is False


def test_disagreement_or_weak_postcut_abstains():
    assert join_source_colour([event()], [postcut("red")])[0]["source_colour"] is None
    assert (
        join_source_colour([event()], [postcut("yellow", "ambiguous")])[0]["source_colour"] is None
    )


def test_duplicate_postcut_shot_rejected():
    with pytest.raises(ValueError, match="Duplicate"):
        join_source_colour([], [postcut("red"), postcut("yellow")])
