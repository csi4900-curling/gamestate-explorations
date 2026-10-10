"""Preserve a frozen timeline and overlay a source-reviewed credits cut."""

import argparse
from hashlib import sha256
import json
from math import floor
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from refine_split_coverage import refined_coverage


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("timeline", "inventory", "terminal_cut", "source_review", "source_sheet",
                 "output"):
        parser.add_argument(f"--{name.replace('_', '-')}", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    timeline, inventory, cut, review = [json.loads(path.read_text()) for path in
                                        (args.timeline, args.inventory,
                                         args.terminal_cut, args.source_review)]
    if (len({timeline["source_sha256"], inventory["source_sha256"],
             cut["source_sha256"], review["source_sha256"]}) != 1
            or inventory["timeline_sha256"] != digest(args.timeline)
            or cut["timeline_sha256"] != digest(args.timeline)
            or review["terminal_cut_artifact_sha256"] != digest(args.terminal_cut)
            or review["source_sheet_sha256"] != digest(args.source_sheet)
            or review["first_low_source_class"] != "closing_credits_full_frame"
            or review["last_aligned_source_class"] != "split_view_visible_house"
            or review["run_id"] != cut["run_id"]):
        parser.error("Cut, source review, or timeline provenance differs")
    first_low = cut["first_sustained_low_sample_s"]
    last_aligned = cut["last_aligned_sample_s"]
    if first_low is None or last_aligned is None or first_low - last_aligned != 1:
        parser.error("No adjacent 1-second cut bracket")
    conservative_stop = floor(first_low)
    if not last_aligned < conservative_stop < first_low:
        parser.error("Conservative integer cut falls outside observed bracket")
    run_id = cut["run_id"]
    if any(row["run_id"] == run_id and row["passage_time_s"] >= conservative_stop
           for row in inventory["rows"]):
        parser.error("A right proposal would leave supported coverage")
    result = refined_coverage(timeline, run_id, conservative_stop)
    result["status"] = "source_reviewed_terminal_credits_coverage_overlay_not_throw_truth"
    result["coverage_overlay_provenance"] = {
        "frozen_timeline_sha256": digest(args.timeline),
        "right_inventory_sha256": digest(args.inventory),
        "terminal_cut_sha256": digest(args.terminal_cut),
        "terminal_source_review_sha256": digest(args.source_review),
        "terminal_source_sheet_sha256": digest(args.source_sheet),
        "model_code_sha256": digest(ROOT / "prototype/refine_split_coverage.py"),
        "runner_sha256": digest(Path(__file__)),
        "observed_cut_bracket_s": [last_aligned, first_low],
        "conservative_supported_stop_s": conservative_stop,
    }
    result["limitations"].extend([
        "The one-second cut bracket is source-sampled, not frame-exact.",
        "Other gaps and within-run occlusions remain uncertain.",
        "The provisional left events and right proposals were not re-detected or relabeled.",
    ])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"supported_runs": [(r["id"], r["interval_s"]) for r in
                                        result["supported_runs"]],
                      "gaps": result["coverage_gaps_s"],
                      "events": len(result["observed_events"])}))


if __name__ == "__main__":
    main()
