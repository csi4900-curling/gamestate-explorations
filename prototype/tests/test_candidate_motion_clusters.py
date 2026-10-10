import pytest

from prototype.candidate_motion_clusters import group_candidate_passages


def row(key, time_s, colour="red", direction="positive_y"):
    return {"id": key, "crossing_time_s": time_s,
            "colour": colour, "view_motion": direction}


def test_groups_same_colour_direction_with_bounded_total_span():
    groups = group_candidate_passages([
        row("A", 10), row("B", 25), row("C", 34), row("D", 40),
        row("E", 42, colour="yellow"), row("F", 44, direction="negative_y")])
    assert [g["member_ids"] for g in groups] == [
        ["A", "B", "C"], ["D"], ["E"], ["F"]]
    assert all(not g["physical_throw_verified"] for g in groups)


def test_duplicate_ids_rejected():
    with pytest.raises(ValueError, match="Duplicate"):
        group_candidate_passages([row("A", 10), row("A", 20)])
