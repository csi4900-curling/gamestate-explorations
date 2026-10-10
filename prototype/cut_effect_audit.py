"""Describe how proposed cut points change local origin-model windows."""

from collections import Counter


def audit_cut_effects(edit_rows, baseline_origins, augmented_origins):
    """Compare only source-time windows; shot IDs change after adding cuts."""
    rows = []
    for edit in edit_rows:
        if not edit["isolated_spike"]:
            continue
        time_s = edit["time_s"]
        old = [r for r in baseline_origins if r["interval_s"][0] < time_s < r["interval_s"][1]]
        left = [r for r in augmented_origins if r["interval_s"][1] == time_s]
        right = [r for r in augmented_origins if r["interval_s"][0] == time_s]
        if len(old) != 1 or len(left) != 1 or len(right) != 1:
            raise ValueError(f"Cut {time_s} lacks a unique origin-window mapping")
        old, left, right = old[0], left[0], right[0]
        pattern = "".join(str(int(r["predicted"])) for r in (old, left, right))
        rows.append(
            {
                "time_s": time_s,
                "old_camera_shot_id": old["shot_id"],
                "pattern_old_left_right": pattern,
                "old": {"interval_s": old["interval_s"], "origin_probability": old["probability"]},
                "left": {
                    "interval_s": left["interval_s"],
                    "origin_probability": left["probability"],
                },
                "right": {
                    "interval_s": right["interval_s"],
                    "origin_probability": right["probability"],
                },
            }
        )
    counts = Counter(row["pattern_old_left_right"] for row in rows)
    return {
        "isolated_edit_count": len(rows),
        "origin_pattern_counts": dict(counts),
        "rows": rows,
        "limitations": [
            "Origin-model response is not a physical throw label or precision/recall score.",
            "Adjacent windows can be shortened by other added cuts in the same original shot.",
            "Motion continuity, colour, counter association and final event fusion require separate audit.",
        ],
    }
