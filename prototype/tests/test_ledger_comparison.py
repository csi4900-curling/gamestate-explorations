import pytest

from prototype.ledger_comparison import compare_ledgers


def event(candidate, counter, window, colour):
    return {"candidate_id": candidate, "counter_id": counter,
            "shot_id": candidate, "release_window_s": window,
            "colour": colour}


def test_counter_matching_exposes_colour_conflict_without_matching_visual_only():
    old = [event("T1", "B1", [10, 20], "yellow")]
    new = [event("T2", "B1", [10, 15], None),
           event("T3", None, [15, 20], "red")]
    result = compare_ledgers(old, new)
    assert result["counter_changes"][0]["change"] == "colour_changed"
    visual = result["augmented_visual_only"][0]
    assert visual["candidate_id"] == "T3"
    assert visual["opposite_run_overlaps"][0]["candidate_id"] == "T1"


def test_duplicate_counter_id_is_rejected():
    with pytest.raises(ValueError, match="Duplicate"):
        compare_ledgers([event("T1", "B1", [0, 1], "red"),
                         event("T2", "B1", [1, 2], "red")], [])
