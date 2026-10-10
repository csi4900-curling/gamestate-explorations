import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from motion_path_dedup import deduplicate_motion_paths


def candidate(cid, time, colour="red"):
    return {"id": cid, "crossing_time_s": time, "colour": colour}


def row(cid, start, end, colour="red", view="right"):
    return {
        "candidate_id": cid,
        "colour": colour,
        "receiving_view": view,
        "selection": {
            "path": [
                {"source_time_s": t, "ground_position_m": [0, 20 - t]} for t in range(start, end)
            ]
        },
    }


def test_suppresses_later_candidate_on_same_timed_path():
    result = deduplicate_motion_paths(
        [candidate("D1", 1), candidate("D2", 3)], [row("D1", 5, 12), row("D2", 6, 14)]
    )
    assert result["retained_candidate_ids"] == ["D1"]
    assert result["pairs"][0]["shared_timed_observation_count"] == 6


def test_colour_or_time_difference_keeps_distinct_events():
    result = deduplicate_motion_paths(
        [candidate("D1", 1), candidate("D2", 3, "yellow")],
        [row("D1", 5, 12), row("D2", 5, 12, "yellow")],
    )
    assert len(result["retained_candidate_ids"]) == 2
