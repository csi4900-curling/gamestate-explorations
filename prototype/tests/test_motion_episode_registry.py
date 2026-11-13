import pytest

from prototype.motion_episode_registry import build_registry


def track(start, *, x=100):
    return {
        "first_seen_s": start,
        "last_seen_s": start + 4,
        "span_px": 32.0,
        "point_count": 4,
        "first_pixel": [x, 200],
        "last_pixel": [x + 30, 190],
    }


def candidate(shot_id, counter_id, red=(), yellow=()):
    return {
        "shot_id": shot_id,
        "counter_id": counter_id,
        "colour_tracks": {"red": list(red), "yellow": list(yellow)},
    }


def test_shared_track_is_one_episode_and_not_unique_throw_support():
    same = track(10)
    result = build_registry(
        [
            candidate("A", "B01", red=[same]),
            candidate("B", None, red=[same]),
            candidate("C", "B02", yellow=[track(30)]),
        ]
    )
    assert result["episode_count"] == 2
    assert result["shared_episode_count"] == 1
    assert result["candidate_motion_status_counts"] == {
        "shared_tracks_only": 2,
        "exclusive_track_available": 1,
    }
    assert result["episodes"][0]["candidate_ids"] == ["A", "B"]
    assert all(not row["distinct_throw_verified"] for row in result["candidates"])


def test_same_time_but_different_pixels_stays_distinct():
    result = build_registry(
        [candidate("A", None, red=[track(10, x=100)]), candidate("B", None, red=[track(10, x=150)])]
    )
    assert result["episode_count"] == 2
    assert result["shared_episode_count"] == 0


def test_duplicate_candidate_id_is_rejected():
    with pytest.raises(ValueError, match="Duplicate"):
        build_registry([candidate("A", None), candidate("A", "B01")])
