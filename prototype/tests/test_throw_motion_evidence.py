import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from throw_motion_evidence import combine_directional_event


def selection(status, time=10):
    if status == "provisional_unique_far_entry_motion_path":
        return {"status": status, "path": [{"source_time_s": time}]}
    if status == "ambiguous_far_entry_motion_paths":
        return {
            "status": status,
            "shared_prefix": [{"source_time_s": time}],
            "first_ambiguity_time_s": time + 1,
        }
    return {"status": status, "path": []}


def event(right, left):
    return {
        "event_id": "C01",
        "reference_colour": "red",
        "reference_window_s": [0, 20],
        "far_entry_selection": selection(right),
        "left_reverse_selection": selection(left),
    }


def test_combines_supported_direction_without_claiming_game_state():
    result = combine_directional_event(
        event("no_supported_far_entry_motion_path", "provisional_unique_far_entry_motion_path")
    )
    assert result["receiving_view"] == "left"
    assert result["sample_count"] == 1
    assert result["simulation_ready"] is False


def test_retains_shared_prefix_and_abstains_on_view_conflict():
    result = combine_directional_event(
        event("ambiguous_far_entry_motion_paths", "no_supported_far_entry_motion_path")
    )
    assert result["status"] == "provisional_prefix_before_identity_ambiguity"
    assert result["first_identity_ambiguity_s"] == 11
    conflict = combine_directional_event(
        event(
            "provisional_unique_far_entry_motion_path", "provisional_unique_far_entry_motion_path"
        )
    )
    assert conflict["status"] == "conflicting_receiving_view_evidence"
    assert conflict["observed_path"] == []
