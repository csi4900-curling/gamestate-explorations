"""Preselect a time-spread source review of matched, clear-context paths."""

import argparse
from hashlib import sha256
import json
from pathlib import Path


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--context", type=Path, required=True)
    parser.add_argument("--run", nargs=2, action="append", metavar=("RUN_ID", "PROBE"),
                        required=True)
    parser.add_argument("--sample-count", type=int, default=12)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error("Output directory already exists")
    inventory = json.loads(args.inventory.read_text())
    context = json.loads(args.context.read_text())
    if context["inventory_sha256"] != digest(args.inventory):
        parser.error("Context and inventory fingerprints differ")
    probe_paths = {run_id: Path(path) for run_id, path in args.run}
    if len(probe_paths) != len(args.run) or set(probe_paths) != set(
            inventory["right_probe_sha256_by_run"]):
        parser.error("One probe per inventory run required")
    probes = {}
    for run_id, path in probe_paths.items():
        probe = json.loads(path.read_text())
        if (digest(path) != inventory["right_probe_sha256_by_run"][run_id]
                or probe["source_sha256"] != inventory["source_sha256"]):
            parser.error(f"{run_id} source lineage differs")
        probes[run_id] = probe
    context_by_id = {row["proposal_id"]: row for row in context["rows"]}
    if len(context_by_id) != len(context["rows"]):
        parser.error("Duplicate context proposal IDs")
    eligible = sorted((row for row in inventory["rows"]
                       if row["temporal_status"] == "one_left_time_colour_candidate"
                       and context_by_id[row["proposal_id"]]["context_tier"] ==
                       "clear_context_review"), key=lambda row: row["passage_time_s"])
    if args.sample_count < 1 or args.sample_count > len(eligible):
        parser.error("Sample count must be within eligible count")
    indices = [int((i + 0.5) * len(eligible) / args.sample_count)
               for i in range(args.sample_count)]
    chosen = [eligible[index] for index in indices]
    args.output_dir.mkdir(parents=True)
    selection = {
        "status": "preselected_time_spread_matched_clear_source_review_not_random_accuracy_sample",
        "source_sha256": inventory["source_sha256"],
        "inventory_sha256": digest(args.inventory),
        "context_sha256": digest(args.context),
        "probe_sha256_by_run": inventory["right_probe_sha256_by_run"],
        "eligible_count": len(eligible),
        "sample_count": len(chosen),
        "sampling_rule": "Sort by right passage time; select floor((i+0.5)*N/n) for i=0..n-1.",
        "rows": [{"proposal_id": row["proposal_id"],
                  "passage_time_s": row["passage_time_s"],
                  "matched_left_event_id": row[
                      "direction_aware_same_colour_left_ids_within_lag"][0]}
                 for row in chosen],
        "limitations": [
            "Time-spread selection is not an independent random sample or precision estimator.",
            "Source review can discover counterexamples but cannot prove all eligible paths are stones.",
        ],
    }
    (args.output_dir / "selection.json").write_text(json.dumps(selection, indent=2) + "\n")
    for run_id, probe in probes.items():
        wanted = {row["raw_track_id"] for row in chosen if row["run_id"] == run_id}
        selected = [row for row in probe["directional_review_proposals"]
                    if row["raw_track_id"] in wanted]
        if len(selected) != len(wanted):
            raise RuntimeError(f"{run_id} selection lost a proposal")
        payload = {
            "status": "time_spread_matched_clear_source_render_subset_not_labels",
            "source_sha256": probe["source_sha256"],
            "source_interval_s": probe["source_interval_s"],
            "source_time_offset_s": probe["source_time_offset_s"],
            "parent_probe_sha256": digest(probe_paths[run_id]),
            "selection_sha256": digest(args.output_dir / "selection.json"),
            "directional_review_proposals": selected,
        }
        (args.output_dir / f"{run_id.lower()}-proposals.json").write_text(
            json.dumps(payload, indent=2) + "\n")
    print(json.dumps({"eligible": len(eligible), "sampled": len(chosen)}))


if __name__ == "__main__":
    main()
