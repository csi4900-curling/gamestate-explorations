import pytest

from prototype.global_motion_links import link_candidate_windows


def episode(name, colour="red", interval=(10, 14), shot="S1"):
    return {
        "episode_id": name,
        "camera_shot_id": shot,
        "colour": colour,
        "interval_s": list(interval),
    }


def shot(name, interval, tracks):
    return {"camera_shot_id": name, "interval_s": list(interval), "tracks": tracks}


def candidate(name, colour, search, delivery):
    return {
        "shot_id": name,
        "counter_id": None,
        "candidate_colour": colour,
        "search_interval_s": list(search),
        "delivery_window_s": list(delivery),
    }


def test_one_source_episode_is_shared_not_duplicated_by_windows():
    result = link_candidate_windows(
        [
            candidate("S1", "red", (8, 16), (8, 11)),
            candidate("S2", "red", (12, 20), (15, 18)),
        ],
        [shot("S1", (0, 16), [episode("E1")]), shot("S2", (16, 30), [])],
    )
    assert result["catalogue_episode_count"] == 1
    assert result["candidate_episode_edge_count"] == 2
    assert result["shared_by_multiple_candidates_episode_count"] == 1
    assert result["candidate_motion_status_counts"] == {"shared_catalogue_tracks_only": 2}
    assert result["episodes"][0]["candidate_ids"] == ["S1", "S2"]
    assert [edge["overlaps_delivery_window"] for edge in result["edges"]] == [True, False]


def test_colour_and_exclusive_end_of_window():
    result = link_candidate_windows(
        [
            candidate("S1", "yellow", (8, 10), (8, 10)),
            candidate("S2", None, (8, 11), (8, 11)),
        ],
        [shot("S1", (0, 20), [episode("E1")])],
    )
    assert result["candidate_episode_edge_count"] == 1
    assert result["candidates"][0]["catalogue_motion_status"] == "no_catalogue_track"
    assert (
        result["candidates"][1]["catalogue_motion_status"] == "exclusive_catalogue_track_available"
    )


def test_episode_crossing_camera_shot_is_rejected():
    with pytest.raises(ValueError, match="camera shot"):
        link_candidate_windows([], [shot("S1", (0, 12), [episode("E1")])])
