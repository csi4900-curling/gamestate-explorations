import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from stone_proposal_path import (first_visible_stability_onset,
                                 select_far_entry_motion_path,
                                 select_single_colour_motion_run)


def row(time, positions):
    return {"source_time_s": time, "views": {"right": {"proposals": [
        {"colour": "red", "pixel_center": [100, 500 - 20 * y],
         "ground_position_m": [0, y]} for y in positions]}}}


def test_selects_continuous_motion_without_filling_missing_samples():
    rows = [row(i * 0.5, [10 - i * 0.7]) for i in range(8)]
    result = select_single_colour_motion_run(rows, "red")
    assert result["status"] == "provisional_unique_same_colour_motion_run"
    assert result["sample_count"] == 8
    assert result["release_time_observed"] is False


def test_stationary_or_ambiguous_candidates_do_not_form_track():
    assert select_single_colour_motion_run(
        [row(i * 0.5, [10]) for i in range(8)], "red")["status"] == "no_supported_motion_run"
    rows = [row(i * 0.5, [10 - i * 0.7]) for i in range(8)]
    rows[4] = row(2.0, [7.2, 7.3])
    assert select_single_colour_motion_run(rows, "red")["status"] == "no_supported_motion_run"


def test_time_order_is_required():
    with pytest.raises(ValueError):
        select_single_colour_motion_run([row(1, [5]), row(0, [4])], "red")


def test_visible_stability_needs_a_full_window():
    path = [{"source_time_s": i * 0.5,
             "pixel_center": [100, 100 + max(0, 5 - i) * 3]}
            for i in range(18)]
    assert first_visible_stability_onset(path) == 2.5
    assert first_visible_stability_onset(path[:12]) is None


def test_far_entry_follows_moving_stone_amid_parked_stone():
    rows = [row(i, [4.0, 16.0 - i * 1.5]) for i in range(8)]
    result = select_far_entry_motion_path(rows, "red")
    assert result["status"] == "provisional_unique_far_entry_motion_path"
    assert result["sample_count"] == 8
    assert result["frames_with_multiple_same_colour_candidates"] == 8


def test_far_entry_abstains_on_stationary_or_two_equally_good_paths():
    stationary = [row(i, [15.0]) for i in range(8)]
    assert select_far_entry_motion_path(stationary, "red")["status"] == "no_supported_far_entry_motion_path"
    duplicate = [row(i, [16.0 - i, 17.0 - i]) for i in range(8)]
    ambiguous = select_far_entry_motion_path(duplicate, "red")
    assert ambiguous["status"] == "ambiguous_far_entry_motion_paths"
    assert ambiguous["shared_prefix_sample_count"] == 0


def test_reverse_direction_recovers_left_receiving_motion():
    rows = [row(i, [-5.5 + i * 1.5]) for i in range(4)]
    for sample in rows:
        sample["views"]["left"] = sample["views"]["right"]
    result = select_far_entry_motion_path(
        rows, "red", view="left", entry_y_threshold_m=-4.5,
        forward_direction=1, min_samples=4)
    assert result["status"] == "provisional_unique_far_entry_motion_path"


def test_missing_sample_requires_explicit_gap_policy():
    rows = [row(i * 0.5, [16 - i * 0.7]) for i in range(8)]
    rows[3] = row(1.5, [])
    rows[3]["status"] = "abstained_no_stable_anchor"
    strict = select_far_entry_motion_path(rows, "red", min_samples=7)
    assert strict["status"] == "no_supported_far_entry_motion_path"
    bridged = select_far_entry_motion_path(
        rows, "red", max_gap_s=1.1, min_samples=7,
        allow_missing_samples=True)
    assert bridged["status"] == "provisional_unique_far_entry_motion_path"
    assert bridged["unobserved_gap_count"] == 1
    assert bridged["unobserved_sample_count"] == 1
    restricted = select_far_entry_motion_path(
        rows, "red", max_gap_s=1.1, min_samples=7,
        allow_missing_samples=True,
        skip_status_required="abstained_no_stable_anchor")
    assert restricted["status"] == "provisional_unique_far_entry_motion_path"
