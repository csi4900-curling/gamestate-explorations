"""Attach repeated scoreboard display context to full candidate handoffs."""

import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.end_marker_temporal import stable_marker_evidence
from prototype.stable_display_run_context import attach_stable_display_runs


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--handoff", type=Path, required=True)
    parser.add_argument("--marker-scan", type=Path, required=True)
    parser.add_argument("--profile", choices=("latvia", "scotland"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve earlier result")
    handoff = json.loads(args.handoff.read_text())
    scan = json.loads(args.marker_scan.read_text())
    if (scan["status"] != "development_2d_registered_broadcast_marker_not_physical_end" or
            scan["video_sha256"] != handoff["source_sha256"]):
        parser.error("Handoff and marker scan source/version differ")
    if args.profile == "latvia":
        source_rows = handoff["ordered_candidates"]
        time_key = "source_time_s"
    else:
        source_rows = handoff["rows"]
        time_key = "observation_time_s"
    if len(source_rows) != handoff["candidate_count" if args.profile == "latvia"
                                        else "candidate_sequence_count"]:
        parser.error("Handoff candidate inventory differs")
    normalized = []
    by_id = {}
    for row in source_rows:
        if (row["game_state_after"]["end_identity"] is not None or
                row["game_state_after"]["simulation_ready"] or
                row["game_state_after"]["spin_revolution_count"] is not None):
            parser.error("Handoff promoted physical state unexpectedly")
        normalized.append({"id": row["candidate_id"],
                           "crossing_time_s": row[time_key],
                           "colour": row["colour_claim"]})
        by_id[row["candidate_id"]] = row
    temporal = stable_marker_evidence(scan["samples"])
    context, _ = attach_stable_display_runs(normalized, temporal["stable_runs"])
    tier_counts = defaultdict(Counter)
    for row in context:
        original = by_id[row["candidate_id"]]
        row["observation_kind"] = original["observation_kind"]
        row["evidence_tier"] = original["evidence_tier"]
        tier_counts[str(row["displayed_end"]) if row["displayed_end"] is not None
                    else "unobserved"][row["observation_kind"]] += 1
    result = {
        "status": "candidate_handoff_with_broadcast_display_context_not_physical_state",
        "source_sha256": handoff["source_sha256"],
        "handoff_sha256": digest(args.handoff),
        "marker_scan_sha256": digest(args.marker_scan),
        "temporal_summarizer_sha256": digest(ROOT / "prototype/end_marker_temporal.py"),
        "joiner_sha256": digest(ROOT / "prototype/stable_display_run_context.py"),
        "runner_sha256": digest(Path(__file__)),
        "profile": args.profile,
        "candidate_count": len(context),
        "context_status_counts": dict(Counter(row["display_context_status"]
                                              for row in context)),
        "observation_kinds_by_displayed_run": {
            end: dict(counts) for end, counts in tier_counts.items()},
        "display_runs": temporal["stable_runs"],
        "candidates": context,
        "limitations": [
            "This sidecar references, but does not rewrite, the full event/partial-state handoff.",
            "Displayed-end graphic can lag physical play; these are not physical end assignments.",
            "Raw and right-only candidates are review proposals, not verified deliveries.",
            "No candidate is inserted, removed or promoted to simulation-ready state.",
        ],
    }
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"candidate_count": len(context),
                      "context_status_counts": result["context_status_counts"],
                      "observation_kinds_by_displayed_run": result[
                          "observation_kinds_by_displayed_run"]}))


if __name__ == "__main__":
    main()
