"""Development replay of short, bracketed split-screen layout gaps.

This does not alter the frozen preflight. Bridged spans are conditional
geometry support, not evidence that every frame or throw is observable.
"""

from copy import deepcopy


def bridge_split_gaps(preflight, *, min_split_samples=4, max_beijing_only=1):
    """Return a replay with only isolated 90 s interior split gaps promoted."""
    if preflight.get("layout_chunk_s") != 90:
        raise ValueError("The bridge rule was defined only for 90-second chunks")
    chunks = deepcopy(preflight["chunks"])
    samples = preflight["samples"]
    promoted = []
    for index in range(1, len(chunks) - 1):
        chunk = chunks[index]
        if (chunk["layout"] != "unknown" or
                chunks[index - 1]["layout"] != "split_2024" or
                chunks[index + 1]["layout"] != "split_2024"):
            continue
        start, end = chunk["interval_s"]
        if end - start != 90 or chunk["samples"] != 9:
            continue
        rows = [row for row in samples if start <= row["time_s"] < end]
        if len(rows) != 9:
            raise ValueError("Saved chunk/sample count differs")
        split = sum(row["split_2024_signature"] for row in rows)
        beijing_only = sum(row["beijing_2022_counter"] and
                           not row["split_2024_signature"] for row in rows)
        if (split < min_split_samples or beijing_only > max_beijing_only or
                split != chunk["split_signature_count"]):
            continue
        chunk["layout"] = "split_2024"
        chunk["bridge_status"] = "conditional_short_interior_gap"
        chunk["bridge_evidence"] = {
            "split_signature_samples": split,
            "sample_count": 9,
            "beijing_only_samples": beijing_only,
        }
        promoted.append([start, end])
    runs = []
    for chunk in chunks:
        kind = chunk["layout"]
        start, end = chunk["interval_s"]
        if runs and runs[-1]["layout"] == kind:
            runs[-1]["interval_s"][1] = end
            runs[-1]["samples"] += chunk["samples"]
        else:
            runs.append({"layout": kind, "interval_s": [start, end],
                         "samples": chunk["samples"]})
    result = deepcopy(preflight)
    result["chunks"] = chunks
    result["runs"] = runs
    result["coverage_gaps_s"] = [row["interval_s"] for row in runs
                                 if row["layout"] == "unknown"]
    kinds = {row["layout"] for row in runs}
    result["layout"] = next(iter(kinds)) if len(kinds) == 1 and "unknown" not in kinds else "unknown"
    result["bridge_promoted_intervals_s"] = promoted
    result["bridge_rule"] = {
        "min_split_samples_of_nine": min_split_samples,
        "max_beijing_only_samples": max_beijing_only,
        "requires_split_on_both_sides": True,
        "requires_exact_90_second_interior_chunk": True,
    }
    return result
