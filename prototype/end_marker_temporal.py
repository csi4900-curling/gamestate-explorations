"""Summarize repeated broadcast end markers without inferring unseen play."""


def stable_marker_evidence(samples, *, min_hits=2):
    if min_hits < 2:
        raise ValueError("At least two marker hits are required")
    hits = [
        (row["time_s"], row["marker"]["end"]) for row in samples if row.get("marker") is not None
    ]
    if any(right[0] <= left[0] for left, right in zip(hits, hits[1:])):
        raise ValueError("Marker observations must have increasing times")
    runs = []
    for time_s, end in hits:
        if runs and runs[-1]["end"] == end:
            runs[-1]["last_hit_s"] = time_s
            runs[-1]["hit_count"] += 1
        else:
            runs.append({"end": end, "first_hit_s": time_s, "last_hit_s": time_s, "hit_count": 1})
    discarded = [run for run in runs if run["hit_count"] < min_hits]
    stable = []
    for run in runs:
        if run["hit_count"] < min_hits:
            continue
        if stable and stable[-1]["end"] == run["end"]:
            stable[-1]["last_hit_s"] = run["last_hit_s"]
            stable[-1]["hit_count"] += run["hit_count"]
        else:
            stable.append(run.copy())
    changes = [
        {
            "from_end": before["end"],
            "to_end": after["end"],
            "last_old_hit_s": before["last_hit_s"],
            "first_new_hit_s": after["first_hit_s"],
        }
        for before, after in zip(stable, stable[1:])
    ]
    return {
        "minimum_hits_per_run": min_hits,
        "stable_runs": stable,
        "discarded_short_runs": discarded,
        "stable_marker_changes": changes,
    }
