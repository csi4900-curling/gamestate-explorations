import pytest

from prototype.corridor_right_episodes import build_corrob_episodes


def row(left_id, t, right_ids, colour="red", direction="positive_y"):
    return {"left_candidate_id": left_id, "left_passage_time_s": t,
            "colour_claim": colour, "direction": direction,
            "matching_right_proposals": [
                {"right_proposal_id": rid} for rid in right_ids]}


def test_groups_shared_right_and_preserves_singletons():
    episodes = build_corrob_episodes([
        row("A", 20, ["R1"]), row("B", 21, ["R1"]),
        row("C", 30, ["R2"]), row("D", 40, []),
    ])
    assert [e["member_left_candidate_ids"] for e in episodes] == [
        ["A", "B"], ["C"], ["D"]]
    assert [e["episode_kind"] for e in episodes] == [
        "shared_one_right_candidate", "one_to_one_time_candidate",
        "no_right_candidate"]
    assert all(not e["physical_throw_count_verified"] for e in episodes)


def test_transitive_multiple_right_ambiguity_not_silently_split():
    episodes = build_corrob_episodes([
        row("A", 10, ["R1"]), row("B", 12, ["R1", "R2"]),
        row("C", 14, ["R2"]),
    ])
    assert len(episodes) == 1
    assert episodes[0]["episode_kind"] == "multiple_right_candidates"
    assert episodes[0]["right_proposal_ids"] == ["R1", "R2"]


def test_rejects_duplicate_left_and_cross_colour_shared_right():
    with pytest.raises(ValueError, match="Duplicate"):
        build_corrob_episodes([row("A", 10, []), row("A", 20, [])])
    with pytest.raises(ValueError, match="colour or direction"):
        build_corrob_episodes([row("A", 10, ["R1"]),
                               row("B", 11, ["R1"], colour="yellow")])


def test_preserves_right_only_proposals_inside_interval():
    episodes = build_corrob_episodes(
        [row("A", 10, ["R1"])],
        right_proposals=[
            {"proposal_id": "R1", "colour_claim": "red", "direction": "positive_y",
             "passage_time_s": 8},
            {"proposal_id": "R2", "colour_claim": "yellow", "direction": "negative_y",
             "passage_time_s": 20},
            {"proposal_id": "R3", "colour_claim": "yellow", "direction": "negative_y",
             "passage_time_s": 40},
        ], interval_s=[0, 30])
    assert [e["episode_kind"] for e in episodes] == [
        "one_to_one_time_candidate", "right_only_candidate"]
    assert episodes[1]["member_left_candidate_ids"] == []
    assert episodes[1]["right_proposal_ids"] == ["R2"]
    assert episodes[1]["observation_time_s"] == 20
