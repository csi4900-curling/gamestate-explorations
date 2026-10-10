"""Attach repeated broadcast end-display runs without assigning physical ends."""

from collections import Counter, defaultdict


def attach_stable_display_runs(events, stable_runs):
    ids = [row["id"] for row in events]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate candidate ID")
    ordered = sorted(stable_runs, key=lambda run: run["first_hit_s"])
    for run in ordered:
        if (run["hit_count"] < 2 or
                run["last_hit_s"] < run["first_hit_s"] or
                not 1 <= run["end"] <= 10):
            raise ValueError("Invalid repeated display run")
    if any(left["last_hit_s"] >= right["first_hit_s"]
           for left, right in zip(ordered, ordered[1:])):
        raise ValueError("Display runs overlap")
    rows = []
    counts = defaultdict(Counter)
    for event in sorted(events, key=lambda row: (row["crossing_time_s"], row["id"])):
        time_s = event["crossing_time_s"]
        matching = [run for run in ordered
                    if run["first_hit_s"] <= time_s <= run["last_hit_s"]]
        if len(matching) > 1:
            raise ValueError("Candidate belongs to multiple display runs")
        run = matching[0] if matching else None
        rows.append({
            "candidate_id": event["id"],
            "crossing_time_s": time_s,
            "colour_claim": event["colour"],
            "display_context_status": (
                "inside_repeated_display_run" if run else "display_run_unobserved"),
            "displayed_end": run["end"] if run else None,
            "supporting_display_run_s": [run["first_hit_s"], run["last_hit_s"]]
            if run else None,
            "physical_end_identity": None,
            "physical_throw_verified": False,
            "simulation_ready": False,
        })
        if run:
            counts[run["end"]][event["colour"]] += 1
    return rows, {str(end): dict(by_colour)
                  for end, by_colour in sorted(counts.items())}
