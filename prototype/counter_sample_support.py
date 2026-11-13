"""Summarize raw broadcast-counter observations around a candidate update."""


def local_counter_support(event, samples, *, near_s=2, far_s=12):
    """Describe, without classifying, raw readings before and after an update."""
    if not 0 <= near_s < far_s:
        raise ValueError("Invalid context window")
    t = event["crossing_time_s"]
    before = [
        row["counts"]
        for row in samples
        if t - far_s <= row["time_s"] <= t - near_s and row["counts"] is not None
    ]
    after = [
        row["counts"]
        for row in samples
        if t + near_s <= row["time_s"] <= t + far_s and row["counts"] is not None
    ]

    def support(readings, expected):
        return {
            "visible_samples": len(readings),
            "expected_samples": sum(row == expected for row in readings),
            "expected_fraction": (
                round(sum(row == expected for row in readings) / len(readings), 4)
                if readings
                else None
            ),
            "distinct_states": sorted({tuple(row) for row in readings}),
        }

    return {
        "counter_id": event["id"],
        "colour": event["colour"],
        "counter_update_s": t,
        "context_window_s": [near_s, far_s],
        "before": support(before, event["remaining_before"]),
        "after": support(after, event["remaining_after"]),
    }
