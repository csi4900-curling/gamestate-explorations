import pytest

from right_variant_review_queue import build_review_queue


def proposal(track, time, *, colour="red", direction="positive_y", episode=1):
    return {"raw_track_id": track, "colour_claim": colour,
            "direction": direction, "passage": {"time_s": time, "pixel": [1, 2]},
            "observed_prefix_interval_s": [time - 1, time],
            "episode_index_within_raw_track": episode}


def test_keeps_all_variant_and_episode_identities_with_bounded_groups():
    variants = {"one": [proposal("A", 0), proposal("B", 14)],
                "two": [proposal("A", 7), proposal("A", 7.1, episode=2)]}
    rows, groups = build_review_queue(variants)
    assert len(rows) == 4
    assert len(groups) == 2  # 0, 7, 14 cannot chain to one group
    assert {row["proposal_id"] for row in rows} == {
        "one:A:1", "one:B:1", "two:A:1", "two:A:2"}
    assert all(g["last_time_s"] - g["first_time_s"] <= 8 for g in groups)
    assert all(not row["physical_throw_identity_verified"] for row in rows)
    assert build_review_queue(variants) == (rows, groups)


def test_different_colour_or_direction_stays_separate():
    _, groups = build_review_queue({"v": [proposal("A", 1),
                                          proposal("B", 1, colour="yellow"),
                                          proposal("C", 1, direction="negative_y")]})
    assert len(groups) == 3


def test_rejects_duplicate_episode_identity():
    with pytest.raises(ValueError, match="Duplicate proposal"):
        build_review_queue({"v": [proposal("A", 1), proposal("A", 2)]})
