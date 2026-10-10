import numpy as np
import pytest

from scene_cuts import scene_cut_evidence, split_points_at_cuts
from stone_motion_fallback import moving_cap_tracks


def observation(t, x):
    return (t, [{"pixel": [x, 100], "bbox": [x - 4, 96, 8, 8]}])


def test_hard_edit_is_distinct_from_small_frame_change():
    dark = np.zeros((360, 640, 3), np.uint8)
    bright_blue = np.full((360, 640, 3), (250, 80, 25), np.uint8)
    assert scene_cut_evidence(dark, bright_blue)["hard_cut"]
    assert not scene_cut_evidence(dark, dark)["hard_cut"]
    with pytest.raises(ValueError):
        scene_cut_evidence(dark, dark[:100])


def test_cut_prevents_greedy_track_from_becoming_one_continuous_identity():
    observations = [observation(i, 100 + i * 10) for i in range(8)]
    assert len(moving_cap_tracks(observations, max_step_px=11)) == 1
    split = moving_cap_tracks(observations, max_step_px=11, cut_times_s=[4])
    assert len(split) == 2
    assert [row["points"][0]["time_s"] for row in split] == [0, 4]
    assert [row["points"][-1]["time_s"] for row in split] == [3, 7]


def test_existing_track_points_split_at_cut_without_dropping_observations():
    points = [{"time_s": t} for t in (0.0, 0.2, 1.0, 1.2)]
    segments = split_points_at_cuts(points, [0.6])
    assert [[row["time_s"] for row in segment] for segment in segments] == [
        [0.0, 0.2], [1.0, 1.2]
    ]
    with pytest.raises(ValueError):
        split_points_at_cuts([points[0], points[0]], [])
