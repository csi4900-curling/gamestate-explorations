import pytest

from prototype.split_board_view_routing import route_split_post_board_views


def sequence():
    return {
        "source_sha256": "source",
        "left_candidate_count": 3,
        "right_proposals": [
            {
                "proposal_id": "A",
                "colour_claim": "yellow",
                "direction": "positive_y",
                "passage_time_s": 5,
            },
            {
                "proposal_id": "B",
                "colour_claim": "red",
                "direction": "negative_y",
                "passage_time_s": 25,
            },
        ],
        "rows": [
            {
                "candidate_id": "S1",
                "observation_kind": "left_tracked_passage",
                "observation_time_s": 10,
                "colour_claim": "yellow",
                "right_temporal_candidate_ids": ["A"],
                "post_candidate_partial_cap_observation": {"status": "none"},
            },
            {
                "candidate_id": "S2",
                "observation_kind": "left_tracked_passage",
                "observation_time_s": 20,
                "colour_claim": "red",
                "right_temporal_candidate_ids": ["B"],
                "post_candidate_partial_cap_observation": {"status": "partial"},
            },
            {
                "candidate_id": "S3",
                "observation_kind": "left_tracked_passage",
                "observation_time_s": 30,
                "colour_claim": "yellow",
                "right_temporal_candidate_ids": [],
            },
        ],
    }


def test_routes_each_direction_and_abstains_without_link():
    routed = route_split_post_board_views(sequence())
    assert [r["conditional_receiving_view"] for r in routed["rows"]] == ["left", "right", None]
    assert routed["existing_right_scan_wrong_view_count_conditional"] == 1
    assert routed["conditional_receiving_view_counts"] == {"left": 1, "right": 1}
    assert all(not r["complete_board_verified"] for r in routed["rows"])


def test_conflicting_direction_order_abstains():
    source = sequence()
    source["right_proposals"][0]["passage_time_s"] = 15
    row = route_split_post_board_views(source)["rows"][0]
    assert row["conditional_receiving_view"] is None
    assert row["routing_status"] == "abstain_direction_order_conflict"


def test_colour_mismatch_rejected():
    source = sequence()
    source["right_proposals"][0]["colour_claim"] = "red"
    with pytest.raises(ValueError, match="colours differ"):
        route_split_post_board_views(source)
