import pytest

from prototype.augmented_scene_cuts import merge_cut_evidence


def edit(time_s, *, isolated=True):
    return {"time_s": time_s, "isolated_spike": isolated,
            "adjacent_pair_metrics": [{}, {"gray_change": 52,
                                           "hist_distance": 0.32,
                                           "hard_cut": False}, {}],
            "gray_isolation_ratio": 3, "hist_isolation_ratio": 2.5}


def test_merge_preserves_provenance_and_abstains_on_nonisolated_change():
    rows = merge_cut_evidence([{"time_s": 1.0, "hard_cut": True}],
                              [edit(2.0), edit(3.0, isolated=False)], 0, 4)
    assert [row["time_s"] for row in rows] == [1, 2]
    assert [row["cut_origin"] for row in rows] == [
        "conservative_hard_cut", "isolated_possible_edit"]


def test_overlapping_proposals_rejected():
    with pytest.raises(ValueError, match="overlap"):
        merge_cut_evidence([{"time_s": 1.0}], [edit(1.2)], 0, 3)


def test_existing_adjacent_hard_cuts_are_preserved():
    rows = merge_cut_evidence([{"time_s": 1.0}, {"time_s": 1.2}],
                              [edit(2.0)], 0, 3)
    assert [row["time_s"] for row in rows] == [1.0, 1.2, 2.0]
