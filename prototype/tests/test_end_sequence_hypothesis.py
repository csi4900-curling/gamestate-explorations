import pytest

from prototype.end_sequence_hypothesis import build_first_end_hypothesis


def fixture():
    official = [
        {"official_shot_id": f"O{i:02}", "team": "A" if i % 2 else "B"} for i in range(1, 17)
    ]
    counters = [{"id": f"B{i:02}", "colour": "red" if i % 2 else "yellow"} for i in range(1, 16)]
    candidates = [
        {"shot_id": f"S{i:02}", "counter_id": f"B{i:02}", "delivery_window_s": [i * 10, i * 10 + 5]}
        for i in range(1, 16)
    ]
    candidates.append({"shot_id": "Sx", "counter_id": None, "delivery_window_s": [75, 80]})
    graph = {
        "candidates": [
            {
                "candidate_id": row["shot_id"],
                "counter_id": row["counter_id"],
                "linked_episode_ids": ["E"] if row["shot_id"] in ("S07", "Sx") else [],
            }
            for row in candidates
        ],
        "episodes": [{"episode_id": "E", "candidate_ids": ["S07", "Sx"]}],
    }
    rescue = {
        "origin_shot_id": "Sfinal",
        "origin_interval_s": [160, 168],
        "receiving_colour": "yellow",
        "receiving_motion_interval_s": [169, 180],
        "receiving_episode_id": "Efinal",
    }
    return candidates, counters, official, graph, rescue


def test_counter_sequence_rescue_and_shared_motion_are_separate_evidence():
    candidates, counters, official, graph, rescue = fixture()
    result = build_first_end_hypothesis(
        candidates,
        counters,
        official,
        {"A": "red", "B": "yellow"},
        graph,
        rescue,
        first_next_end_start_s=200,
    )
    assert len(result["rows"]) == 16
    assert result["rows"][-1]["video_candidate_shot_id"] == "Sfinal"
    assert result["counterless_shared_motion_review"][0][
        "shared_with_counter_backed_candidates"
    ] == ["S07"]
    assert all(not row["physical_stone_identity_verified"] for row in result["rows"])


def test_counter_colour_conflict_rejected():
    candidates, counters, official, graph, rescue = fixture()
    counters[0]["colour"] = "yellow"
    with pytest.raises(ValueError, match="colour disagree"):
        build_first_end_hypothesis(
            candidates,
            counters,
            official,
            {"A": "red", "B": "yellow"},
            graph,
            rescue,
            first_next_end_start_s=200,
        )
