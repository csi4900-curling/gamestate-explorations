"""Source-reviewed terminal camera cut overlay for a routed match timeline."""

from copy import deepcopy


def refined_coverage(timeline, run_id, supported_stop_s):
    result = deepcopy(timeline)
    runs = result["supported_runs"]
    matched = [row for row in runs if row["id"] == run_id]
    if len(matched) != 1 or matched[0]["layout"] != "split_2024":
        raise ValueError("Expected one routed split-view run")
    run = matched[0]
    start, old_stop = run["interval_s"]
    if not start < supported_stop_s < old_stop:
        raise ValueError("Refined stop must shorten the supported run")
    if any(supported_stop_s <= row["crossing_time_s"] < old_stop
           for row in result["observed_events"]):
        raise ValueError("Provisional left event would leave supported coverage")
    run["interval_s"] = [start, supported_stop_s]
    run["source_reviewed_terminal_cut_status"] = "closing_credits_after_last_aligned_sample"
    first, last = result["source_interval_s"]
    cursor = first
    gaps = []
    for item in sorted(runs, key=lambda row: row["interval_s"][0]):
        a, b = item["interval_s"]
        if a < cursor or not a < b or b > last:
            raise ValueError("Invalid or overlapping supported runs")
        if a > cursor:
            gaps.append([cursor, a])
        cursor = b
    if cursor < last:
        gaps.append([cursor, last])
    result["coverage_gaps_s"] = gaps
    result["supported_duration_s"] = sum(
        row["interval_s"][1] - row["interval_s"][0] for row in runs)
    result["coverage_gap_duration_s"] = sum(b - a for a, b in gaps)
    if result["supported_duration_s"] + result["coverage_gap_duration_s"] != last - first:
        raise ValueError("Coverage intervals do not partition source duration")
    return result
