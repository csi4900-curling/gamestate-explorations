import pytest

from prototype.partial_episode_union import build_partial_episode_union


def fixtures():
    handoff = {
        "timeline": [
            {
                "candidate_id": "A",
                "event_status": "provisional_event",
                "candidate_colour": "yellow",
                "passage_time_s": 10.0,
            },
            {
                "candidate_id": "S21",
                "event_status": "screen_abstention",
                "candidate_colour": "red",
                "passage_time_s": 20.0,
            },
            {
                "candidate_id": "S22",
                "event_status": "screen_abstention",
                "candidate_colour": "red",
                "passage_time_s": 24.0,
            },
            {
                "candidate_id": "S23",
                "event_status": "screen_abstention",
                "candidate_colour": "red",
                "passage_time_s": 33.0,
            },
        ]
    }
    prefix = {
        "proposals": [
            {
                "candidate_id": "S21",
                "colour": "red",
                "receiving_view": "right",
                "prefix_samples": [
                    {
                        "source_time_s": t,
                        "pixel_center": [100, 100 - t],
                        "ground_position_m": [0, 30 - t],
                    }
                    for t in (22.0, 23.0, 24.0, 25.0)
                ],
                "first_ambiguity_time_s": 25.5,
                "prefix_sample_count": 4,
                "scored_patch_count": 3,
                "positive_patch_count": 2,
                "conditional_endpoint_displacement_m": 3.0,
            }
        ]
    }
    motion = {
        "rows": [
            {"candidate_id": "S21", "receiving_view": "right", "selection": {"path": None}},
            {"candidate_id": "S22", "receiving_view": "left", "selection": {"path": None}},
            {"candidate_id": "S23", "receiving_view": "right", "selection": {"path": None}},
        ]
    }
    return handoff, prefix, motion


def test_groups_only_overlapping_abstention_and_preserves_all_candidates():
    handoff, prefix, motion = fixtures()
    result = build_partial_episode_union(handoff, prefix, motion)
    assert len(result["episodes"]) == 1
    episode = result["episodes"][0]
    assert episode["candidate_ids"] == ["S21", "S22"]
    assert episode["candidate_passage_times_s"] == {"S21": 20.0, "S22": 24.0}
    assert episode["observed_interval_s"] == [22.0, 25.0]
    assert episode["overlapping_passages"][0]["view_matches_observed_prefix"] is False
    assert episode["physical_throw_identity_verified"] is False
    assert episode["simulation_ready"] is False
    assert [row["candidate_id"] for row in result["candidate_rows"]] == ["A", "S21", "S22", "S23"]
    assert result["candidate_rows"][2]["partial_episode_role"] == "overlapping_passage"
    assert result["candidate_rows"][3]["partial_episode_id"] is None


def test_accepted_same_colour_overlap_is_a_conflict_not_silently_merged():
    handoff, prefix, motion = fixtures()
    handoff["timeline"][0]["candidate_colour"] = "red"
    handoff["timeline"][0]["passage_time_s"] = 23.0
    with pytest.raises(ValueError, match="Accepted same-colour"):
        build_partial_episode_union(handoff, prefix, motion)


def test_prefix_must_precede_ambiguity():
    handoff, prefix, motion = fixtures()
    prefix["proposals"][0]["first_ambiguity_time_s"] = 24.0
    with pytest.raises(ValueError, match="extends past first ambiguity"):
        build_partial_episode_union(handoff, prefix, motion)


def test_separately_tracked_passage_is_not_silently_grouped():
    handoff, prefix, motion = fixtures()
    motion["rows"][1]["selection"]["path"] = [{"source_time_s": 24.0}]
    result = build_partial_episode_union(handoff, prefix, motion)
    assert result["episodes"][0]["candidate_ids"] == ["S21"]
    assert result["candidate_rows"][2]["partial_episode_id"] is None
