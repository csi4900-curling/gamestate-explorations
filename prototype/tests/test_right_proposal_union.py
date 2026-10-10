import pytest

from right_proposal_union import union_right_proposals


def lane(source, raw_id):
    return {"source_sha256": source, "source_interval_s": [1650, 2760],
            "source_time_offset_s": 0,
            "directional_review_proposals": [{
                "raw_track_id": raw_id, "colour_claim": "red",
                "passage": {"time_s": 1700},
                "observed_prefix_interval_s": [1699, 1701],
                "observed_prefix_points": [{"time_s": 1699, "pixel": [400, 300]}]}]}


def test_same_time_proposals_remain_separate_and_namespaced():
    rows = union_right_proposals(lane("hash", "B001"), lane("hash", "B001"),
                                first_lane="greedy", second_lane="area")
    assert [row["proposal_id"] for row in rows] == ["area:B001", "greedy:B001"]
    assert all(not row["physical_throw_identity_verified"] for row in rows)


def test_different_sources_cannot_be_joined():
    with pytest.raises(ValueError, match="same source"):
        union_right_proposals(lane("one", "B001"), lane("two", "A001"),
                              first_lane="greedy", second_lane="area")
