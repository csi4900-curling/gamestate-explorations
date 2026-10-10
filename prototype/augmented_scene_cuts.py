"""Experimental camera-shot split points from hard cuts and isolated edits."""


def merge_cut_evidence(hard_rows, edit_rows, start_s, end_s, *, exclusion_s=0.3):
    """Merge distinct edit proposals without claiming that they are true cuts."""
    hard_times = [row["time_s"] for row in hard_rows]
    if hard_times != sorted(set(hard_times)):
        raise ValueError("Hard cuts must be strictly ordered")
    selected = [row for row in edit_rows if row["isolated_spike"]]
    edit_times = [row["time_s"] for row in selected]
    if edit_times != sorted(set(edit_times)):
        raise ValueError("Selected edit proposals must be strictly ordered")
    all_times = sorted(hard_times + edit_times)
    if (any(not start_s < t < end_s for t in all_times) or
            any(any(abs(t - h) <= exclusion_s for h in hard_times)
                for t in edit_times) or
            any(b - a <= exclusion_s for a, b in zip(edit_times, edit_times[1:]))):
        raise ValueError("Cut proposals overlap or fall outside the source interval")
    result = [dict(row, cut_origin="conservative_hard_cut") for row in hard_rows]
    for row in selected:
        if row["adjacent_pair_metrics"][1]["hard_cut"]:
            raise ValueError("Isolated proposal is already a hard cut")
        result.append({"time_s": row["time_s"],
                       **row["adjacent_pair_metrics"][1],
                       "cut_origin": "isolated_possible_edit",
                       "isolated_spike": True,
                       "gray_isolation_ratio": row["gray_isolation_ratio"],
                       "hist_isolation_ratio": row["hist_isolation_ratio"]})
    return sorted(result, key=lambda row: row["time_s"])
