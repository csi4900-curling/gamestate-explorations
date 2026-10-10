"""Later moving stones may correct an episode's early colour distractor."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from episode_colour_support import refine_episode_colours


def test_stronger_nearby_stone_corrects_colour_without_moving_event_time():
    candidates = [
        {"id": "R", "colour": "red", "crossing_time_s": 10},
        {"id": "Y", "colour": "yellow", "crossing_time_s": 16},
        {"id": "R-later", "colour": "red", "crossing_time_s": 40},
    ]
    decisions = [
        {"id": "R", "status": "corroborated_gap_candidate", "episode_anchor_id": "R",
         "moving_steps_gt4px": 6, "median_local_ice_fraction": 0.6},
        {"id": "Y", "status": "withheld", "episode_anchor_id": "R",
         "moving_steps_gt4px": 18, "median_local_ice_fraction": 0.9},
        {"id": "R-later", "status": "withheld", "episode_anchor_id": "R",
         "moving_steps_gt4px": 50, "median_local_ice_fraction": 0.9},
    ]
    assert refine_episode_colours(candidates, decisions) == [{
        "id": "R", "colour": "yellow", "original_colour": "red",
        "colour_support_id": "Y", "own_moving_steps": 6,
        "challenger_moving_steps": 18, "colour_changed": True,
    }]


def test_weak_or_background_opposite_track_cannot_flip_colour():
    candidates = [
        {"id": "R", "colour": "red", "crossing_time_s": 10},
        {"id": "Y", "colour": "yellow", "crossing_time_s": 14},
    ]
    decisions = [
        {"id": "R", "status": "corroborated_gap_candidate", "episode_anchor_id": "R",
         "moving_steps_gt4px": 20, "median_local_ice_fraction": 0.8},
        {"id": "Y", "status": "withheld", "episode_anchor_id": "R",
         "moving_steps_gt4px": 25, "median_local_ice_fraction": 0.9},
    ]
    assert refine_episode_colours(candidates, decisions)[0]["colour"] == "red"
    decisions[1]["moving_steps_gt4px"] = 40
    decisions[1]["median_local_ice_fraction"] = 0.3
    assert refine_episode_colours(candidates, decisions)[0]["colour"] == "red"
