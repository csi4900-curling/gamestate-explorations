"""Two observation channels agree only when they follow the same object."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cross_channel_motion import cross_channel_pairs


def test_spatially_aligned_tracks_form_pair_but_distant_track_does_not():
    def track(identifier, colour, offset):
        return {
            "id": identifier,
            "colour": colour,
            "crossing_time_s": 10.0,
            "visual_track_points": [
                {"time_s": round(10 + i * 0.2, 1), "pixel": [100 + i * 5 + offset, 150]}
                for i in range(12)
            ],
        }

    learned = [track("box", "red", 0)]
    caps = [
        track("same", "red", 4),
        track("distant", "red", 80),
        track("wrong-colour", "yellow", 0),
    ]
    box_context = [{"id": "box", "moving_steps_gt4px": 11, "live_overlay_sample_fraction": 1.0}]
    cap_context = [
        {
            "id": item["id"],
            "moving_steps_gt4px": 11,
            "median_local_ice_fraction": 0.9,
            "live_overlay_sample_fraction": 1.0,
        }
        for item in caps
    ]
    pairs = cross_channel_pairs(learned, box_context, caps, cap_context)
    assert len(pairs) == 1
    assert pairs[0]["cap_id"] == "same"
    assert pairs[0]["median_position_difference_px"] == 4
