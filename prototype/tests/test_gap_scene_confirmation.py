"""Gap screening should retain a delivery episode, not its every moving stone."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gap_scene_confirmation import confirm_gap_episodes


def candidate(name, colour, start, end):
    return {
        "id": name,
        "colour": colour,
        "crossing_time_s": start,
        "evidence_interval_s": [start, end],
    }


def context(name, fraction):
    return {"id": name, "median_ice_scene_fraction": fraction}


def test_fragment_and_displaced_stone_are_one_episode():
    items = [
        candidate("red-first", "red", 10, 20),
        candidate("red-fragment", "red", 24, 31),
        candidate("yellow-hit", "yellow", 25, 31),
    ]
    rows = [context("red-first", 0.8), context("red-fragment", 0.4), context("yellow-hit", 0.4)]
    decisions = confirm_gap_episodes(items, rows)
    assert [row["status"] for row in decisions] == [
        "corroborated_gap_candidate",
        "withheld",
        "withheld",
    ]
    assert decisions[2]["reason"] == "same_motion_episode"


def test_crowd_track_is_withheld_by_scene_context():
    decisions = confirm_gap_episodes([candidate("crowd", "red", 50, 55)], [context("crowd", 0.07)])
    assert decisions[0]["reason"] == "non_ice_scene"


def test_simultaneous_opposite_colours_remain_ambiguous():
    items = [candidate("red", "red", 10, 15), candidate("yellow", "yellow", 11, 16)]
    rows = [context("red", 0.8), context("yellow", 0.8)]
    decisions = confirm_gap_episodes(items, rows)
    assert all(row["reason"] == "ambiguous_simultaneous_colours" for row in decisions)
