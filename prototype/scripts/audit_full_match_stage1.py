"""Verify a full-match span sweep and group candidates by displayed-end runs."""

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256  # noqa: E402


def require(actual, expected, label):
    if actual != expected:
        raise ValueError(f"{label} differs")


def audit(full_raw, full_corridor, interval_raw, interval_corridor,
          marker_scan, summary, hashes):
    if full_raw["source_interval_s"][0] != 0:
        raise ValueError("Expected a full-match scan from source zero")
    for data in (full_corridor, interval_raw, interval_corridor):
        require(data["source_id"], full_raw["source_id"], "source ID")
        require(data["source_sha256"], full_raw["source_sha256"], "source fingerprint")
    require(marker_scan["video_sha256"], full_raw["source_sha256"],
            "end-marker source fingerprint")
    require(hashes["video"], full_raw["source_sha256"], "full video fingerprint")
    for data in (full_raw, interval_raw):
        require(data["model_sha256"], file_sha256(ROOT / "prototype/span_passage_detection.py"),
                "span model code")
        require(data["baseline_sha256"], file_sha256(ROOT / "prototype/throw_detection.py"),
                "span candidate code")
        require(data["runner_sha256"], file_sha256(ROOT / "prototype/scripts/run_span_probe.py"),
                "span runner code")
    for data in (full_corridor, interval_corridor):
        require(data["model_sha256"], file_sha256(ROOT / "prototype/passage_corridor.py"),
                "corridor model code")
        require(data["runner_sha256"], file_sha256(ROOT / "prototype/scripts/screen_corridor.py"),
                "corridor runner code")
    require(full_corridor["input_sha256"], hashes["full_raw"], "full corridor input")
    require(interval_corridor["input_sha256"], hashes["interval_raw"],
            "interval corridor input")
    for field in ("model_sha256", "baseline_sha256", "runner_sha256", "config"):
        require(full_raw[field], interval_raw[field], f"raw {field}")
    for field in ("model_sha256", "runner_sha256", "geometry"):
        require(full_corridor[field], interval_corridor[field], f"corridor {field}")
    game = next((row for row in summary["games"]
                 if row["video_sha256"] == full_raw["source_sha256"]), None)
    if game is None or game["scan_sha256"] != hashes["marker_scan"]:
        raise ValueError("End-marker summary does not match this source and scan")
    runs = game["stable_runs"]
    if any(a["last_hit_s"] >= b["first_hit_s"] for a, b in zip(runs, runs[1:])):
        raise ValueError("Displayed-end runs overlap")
    raw_events = full_raw["events"]
    screened = full_corridor["screened_events"]
    if ([row["id"] for row in screened] != [row["id"] for row in raw_events] or
            len({row["id"] for row in raw_events}) != len(raw_events)):
        raise ValueError("Full candidate coverage differs")
    accepted = {row["id"] for row in full_corridor["events"]}
    withheld = {row["id"] for row in full_corridor["withheld_events"]}
    if accepted & withheld or accepted | withheld != {row["id"] for row in raw_events}:
        raise ValueError("Full corridor partition differs")
    require(accepted, {row["id"] for row in screened
                       if row["status"] == "ice_corridor_candidate"},
            "corridor statuses")

    start, end = interval_raw["source_interval_s"]
    full_subsequence = [row for row in raw_events if start <= row["crossing_time_s"] < end]
    interval_events = interval_raw["events"]
    require(len(full_subsequence), len(interval_events), "interval candidate count")
    full_screen_by_id = {row["id"]: row for row in screened}
    interval_screen_by_id = {row["id"]: row for row in interval_corridor["screened_events"]}
    differing_fields = []
    id_pairs = []
    for local, global_row in zip(interval_events, full_subsequence):
        for field in ("crossing_time_s", "colour", "crossing_x_px", "passage_y_px"):
            require(local[field], global_row[field], f"interval {local['id']} {field}")
        differences = [field for field in local
                       if field not in ("id", "track_id") and
                       local[field] != global_row[field]]
        if differences:
            differing_fields.append({"interval_id": local["id"],
                                     "full_id": global_row["id"],
                                     "fields": differences})
        local_screen = interval_screen_by_id[local["id"]]
        full_screen = full_screen_by_id[global_row["id"]]
        require(local_screen["status"], full_screen["status"],
                f"corridor decision {local['id']}")
        id_pairs.append({"interval_id": local["id"], "full_id": global_row["id"]})

    def summarize(rows):
        ids = [row["id"] for row in rows]
        return {"raw_candidate_count": len(rows),
                "corridor_candidate_count": sum(row["id"] in accepted for row in rows),
                "withheld_candidate_count": sum(row["id"] in withheld for row in rows),
                "first_candidate_time_s": rows[0]["crossing_time_s"] if rows else None,
                "last_candidate_time_s": rows[-1]["crossing_time_s"] if rows else None,
                "candidate_ids": ids}

    assigned = set()
    by_run = []
    for run in runs:
        rows = [row for row in raw_events
                if run["first_hit_s"] <= row["crossing_time_s"] <= run["last_hit_s"]]
        assigned.update(row["id"] for row in rows)
        by_run.append({"displayed_end": run["end"],
                       "first_marker_hit_s": run["first_hit_s"],
                       "last_marker_hit_s": run["last_hit_s"],
                       "marker_hit_count": run["hit_count"],
                       **summarize(rows)})
    gaps = [(0, runs[0]["first_hit_s"])] + [
        (a["last_hit_s"], b["first_hit_s"]) for a, b in zip(runs, runs[1:])
    ] + [(runs[-1]["last_hit_s"], full_raw["source_interval_s"][1])]
    gap_rows = []
    for left, right in gaps:
        rows = [row for row in raw_events if row["id"] not in assigned and
                left <= row["crossing_time_s"] <= right]
        assigned.update(row["id"] for row in rows)
        gap_rows.append({"marker_gap_s": [left, right], **summarize(rows)})
    require(assigned, {row["id"] for row in raw_events}, "display-run candidate coverage")
    return {
        "status": "verified_full_match_stage1_candidate_coverage_not_throw_segmentation",
        "source_id": full_raw["source_id"],
        "source_sha256": full_raw["source_sha256"],
        "source_interval_s": full_raw["source_interval_s"],
        "input_sha256": hashes,
        "full_raw_candidate_count": len(raw_events),
        "full_corridor_candidate_count": len(accepted),
        "full_withheld_candidate_count": len(withheld),
        "interval_reconciliation": {
            "interval_s": interval_raw["source_interval_s"],
            "matched_candidate_count": len(id_pairs),
            "candidate_id_pairs": id_pairs,
            "non_id_field_differences": differing_fields,
            "all_corridor_decisions_match": True,
        },
        "display_run_rows": by_run,
        "marker_gap_rows": gap_rows,
        "display_run_candidate_total": sum(row["raw_candidate_count"] for row in by_run),
        "marker_gap_candidate_total": sum(row["raw_candidate_count"] for row in gap_rows),
        "candidate_colour_counts": dict(Counter(row["colour"] for row in raw_events)),
        "limitations": [
            "Span and corridor candidates are not confirmed throws or exact segment boundaries.",
            "Broadcast displayed-end runs can lag physical ends and omit graphic gaps.",
            "No high-resolution full-match receiving-path screen or independent exhaustive labels were run.",
            "Official end shot counts cannot supply event timestamps or F1.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("video", "full-raw", "full-corridor", "interval-raw",
                "interval-corridor", "marker-scan", "temporal-summary", "output"):
        parser.add_argument(f"--{key}", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Audit output already exists")
    paths = {key: getattr(args, key.replace("-", "_")) for key in
             ("full-raw", "full-corridor", "interval-raw", "interval-corridor",
              "marker-scan", "temporal-summary")}
    data = {key.replace("-", "_"): json.loads(path.read_text())
            for key, path in paths.items()}
    hashes = {key.replace("-", "_"): file_sha256(path)
              for key, path in paths.items()}
    hashes["video"] = file_sha256(args.video)
    result = audit(data["full_raw"], data["full_corridor"],
                   data["interval_raw"], data["interval_corridor"],
                   data["marker_scan"], data["temporal_summary"], hashes)
    result["runner_sha256"] = file_sha256(Path(__file__))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(result["full_raw_candidate_count"], result["full_corridor_candidate_count"],
          result["interval_reconciliation"]["matched_candidate_count"])


if __name__ == "__main__":
    main()
