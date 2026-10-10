"""Compare per-second Beijing counter visibility with routed timelines."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256


def compare_route(audit, timeline, route):
    start, end = audit["source_interval_s"]
    unknown = {
        second for lo, hi in route["coverage_gaps_s"]
        for second in range(int(lo), int(hi))
    }
    visible = {
        row["time_s"] for row in audit["counter_samples"]
        if row["counts"] is not None
    }
    total = set(range(start, end))
    return {
        "layout_chunk_s": route["layout_chunk_s"],
        "declared_unknown_s": len(unknown),
        "counter_readable_in_declared_unknown_s": len(unknown & visible),
        "counter_unreadable_in_declared_supported_s": len((total - unknown) - visible),
        "counter_readable_in_declared_supported_s": len(visible - unknown),
        "timeline_events_in_declared_unknown": [
            {"id": row["id"], "colour": row["colour"], "crossing_time_s": row["crossing_time_s"]}
            for row in timeline["observed_events"]
            if int(row["crossing_time_s"]) in unknown
        ],
        "counter_events_in_declared_unknown": [
            {"id": row["id"], "colour": row["colour"],
             "crossing_time_s": row["crossing_time_s"],
             "evidence_interval_s": row["evidence_interval_s"]}
            for row in audit["counter_events"]
            if int(row["crossing_time_s"]) in unknown
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--timeline", type=Path, required=True)
    parser.add_argument("--preflight", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve earlier reconciliation")
    audit = json.loads(args.audit.read_text())
    timeline = json.loads(args.timeline.read_text())
    routes = [json.loads(path.read_text()) for path in args.preflight]
    sources = [timeline, *routes]
    if any(row["source_sha256"] != audit["source_sha256"]
           or row["source_interval_s"] != audit["source_interval_s"]
           for row in sources):
        parser.error("Audit, timeline and preflights must cover one source interval")
    audit_keys = {(row["colour"], row["crossing_time_s"]) for row in audit["counter_events"]}
    timeline_keys = {(row["colour"], row["crossing_time_s"])
                     for row in timeline["observed_events"]}
    result = {
        "status": "development_counter_vs_routed_coverage_reconciliation",
        "source_id": audit["source_id"],
        "source_sha256": audit["source_sha256"],
        "source_interval_s": audit["source_interval_s"],
        "audit_sha256": file_sha256(args.audit),
        "timeline_sha256": file_sha256(args.timeline),
        "preflight_sha256": [file_sha256(path) for path in args.preflight],
        "runner_sha256": file_sha256(__file__),
        "sample_count": audit["sample_count"],
        "counter_readable_seconds": audit["visible_sample_count"],
        "counter_unreadable_seconds": audit["sample_count"] - audit["visible_sample_count"],
        "counter_event_count": len(audit["counter_events"]),
        "routed_observed_event_count": len(timeline["observed_events"]),
        "exact_colour_time_matches": len(audit_keys & timeline_keys),
        "counter_only": [row for row in audit["counter_events"]
                         if (row["colour"], row["crossing_time_s"]) not in timeline_keys],
        "timeline_only": [row for row in timeline["observed_events"]
                          if (row["colour"], row["crossing_time_s"]) not in audit_keys],
        "routes": [compare_route(audit, timeline, route) for route in routes],
        "limitations": [
            "Exact timestamp disagreement can be one delayed broadcast update, not a different physical throw.",
            "Readable graphic seconds are not a complete throw reference; unreadable seconds remain unknown.",
            "Layout preflight is sampled, while counter readability is sampled once per second.",
            "No full-recording F1 is inferred from this reconciliation.",
        ],
    }
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"exact_matches": result["exact_colour_time_matches"],
                      "counter_only": len(result["counter_only"]),
                      "timeline_only": len(result["timeline_only"])}))


if __name__ == "__main__":
    main()
