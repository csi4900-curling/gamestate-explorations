"""Attach source-activity limitations to a routed candidate evidence handoff.

Layout coverage and left-trigger coverage are different claims. Right-view
observations remain available when the left delivery panel is static.
"""

from copy import deepcopy


def _inside(t, interval):
    return interval[0] <= t < interval[1]


def attach_left_trigger_coverage(handoff, activity):
    if handoff["source_sha256"] != activity["source_sha256"]:
        raise ValueError("Source videos differ")
    if handoff["input_sha256"]["timeline"] != activity["timeline_sha256"]:
        raise ValueError("Frozen timelines differ")
    runs = {row["id"]: row["interval_s"] for row in handoff["supported_runs"]}
    if len(runs) != len(handoff["supported_runs"]):
        raise ValueError("Duplicate routed run")
    blind = []
    for row in activity["newly_unsupported_intervals"]:
        if row["reason"] != "left_panel_static_while_right_panel_active":
            raise ValueError("Unknown source-activity reason")
        run_id, interval = row["source_run_id"], row["interval_s"]
        if (run_id not in runs or len(interval) != 2 or
                not runs[run_id][0] <= interval[0] < interval[1] <= runs[run_id][1]):
            raise ValueError("Blind interval is outside refined routed support")
        blind.append({"source_run_id": run_id, "interval_s": interval,
                      "reason": row["reason"],
                      "median_left_mae": row["median_left_mae"],
                      "median_right_mae": row["median_right_mae"]})
    blind.sort(key=lambda row: (row["source_run_id"], row["interval_s"][0]))
    for previous, current in zip(blind, blind[1:]):
        if (previous["source_run_id"] == current["source_run_id"] and
                previous["interval_s"][1] > current["interval_s"][0]):
            raise ValueError("Overlapping blind intervals")
    blind_seconds = sum(row["interval_s"][1] - row["interval_s"][0]
                        for row in blind)
    if blind_seconds != activity["newly_unsupported_seconds"]:
        raise ValueError("Source-activity duration does not match blind intervals")
    result = deepcopy(handoff)
    result["left_trigger_blind_intervals"] = blind
    result["left_trigger_supported_intervals"] = []
    for run_id, (start, stop) in runs.items():
        for item in (row for row in blind if row["source_run_id"] == run_id):
            cut_start, cut_stop = item["interval_s"]
            if start < cut_start:
                result["left_trigger_supported_intervals"].append(
                    {"source_run_id": run_id, "interval_s": [start, cut_start]})
            start = cut_stop
        if start < stop:
            result["left_trigger_supported_intervals"].append(
                {"source_run_id": run_id, "interval_s": [start, stop]})
    result["left_trigger_blind_seconds"] = blind_seconds
    blind_candidates = []
    for row in result["rows"]:
        matched = [item for item in blind if _inside(row["observation_time_s"],
                                                      item["interval_s"])]
        if len(matched) > 1:
            raise ValueError("Candidate falls in multiple blind intervals")
        if matched and row["observation_kind"] == "left_tracked_passage":
            raise ValueError("Left-trigger event inside its static blind interval")
        row["left_trigger_coverage"] = (
            "source_activity_blind_right_view_observation_only" if matched
            else "within_sampled_left_activity_support")
        if matched:
            blind_candidates.append(row["candidate_id"])
    result["right_view_candidate_ids_in_left_trigger_blind_interval"] = blind_candidates
    result["complete_throw_sequence_verified"] = False
    result["limitations"].append(
        "Five-second source-activity sampling flags left-trigger blind intervals; "
        "it cannot prove continuous coverage or count omitted throws. "
        "Right-view observations inside a blind interval remain review proposals.")
    return result
