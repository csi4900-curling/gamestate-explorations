"""Join source-observed scoreboard context to conserved raw trigger rows."""

from collections import Counter, defaultdict


def attach_display_context(union, display):
    if union["source_sha256"] != display["source_sha256"]:
        raise ValueError("Source fingerprints differ")
    if union["input_sha256"]["raw"] != display["raw_sha256"]:
        raise ValueError("Raw trigger lineage differs")
    by_id = {row["event_id"]: row for row in display["events"]}
    if len(by_id) != len(display["events"]) or set(by_id) != {
        row["candidate_id"] for row in union["raw_candidates"]
    }:
        raise ValueError("Displayed-end context must cover every raw trigger once")
    rows = []
    counts = defaultdict(Counter)
    for source_row in union["raw_candidates"]:
        row = dict(source_row)
        context = by_id[row["candidate_id"]]
        if abs(row["passage_time_s"] - context["crossing_time_s"]) > 1e-6:
            raise ValueError("Candidate and display-context timestamps differ")
        row["broadcast_display_context"] = context
        row["physical_end_identity"] = None
        rows.append(row)
        if context["display_context_status"] == "bracketed_display_end":
            counts[context["displayed_end"]][row["tier"]] += 1
    return {
        "raw_trigger_count": len(rows),
        "context_status_counts": dict(
            Counter(row["broadcast_display_context"]["display_context_status"] for row in rows)
        ),
        "bracketed_candidate_tiers_by_displayed_end": {
            str(end): dict(tiers) for end, tiers in sorted(counts.items())
        },
        "raw_candidates": rows,
        "simulation_ready_count": 0,
    }
