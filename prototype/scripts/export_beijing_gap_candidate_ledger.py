"""Export source-hashed full-match Beijing candidate evidence across route gaps."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from beijing_gap_candidate_ledger import build_gap_candidate_ledger


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("timeline", "counter-gaps", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--visual-gaps", type=Path)
    parser.add_argument("--visual-parent-timeline", type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists")
    timeline = json.loads(args.timeline.read_text())
    counter = json.loads(args.counter_gaps.read_text())
    visual = json.loads(args.visual_gaps.read_text()) if args.visual_gaps else None
    if args.visual_parent_timeline and not visual:
        parser.error("Visual parent timeline requires visual gaps")
    if visual:
        parent_path = args.visual_parent_timeline or args.timeline
        if visual["timeline_sha256"] != digest(parent_path):
            raise ValueError("Visual gap scan used a different parent timeline")
        if args.visual_parent_timeline:
            parent = json.loads(parent_path.read_text())
            for key in ("source_id", "source_sha256", "source_interval_s",
                        "coverage_gaps_s"):
                if parent[key] != timeline[key]:
                    raise ValueError("Visual parent and current route coverage differ")
    rows = build_gap_candidate_ledger(timeline, counter, visual)
    output = {
        "status": "full_match_candidate_evidence_with_unknown_route_gaps_not_throw_truth",
        "source_id": timeline["source_id"],
        "source_sha256": timeline["source_sha256"],
        "source_interval_s": timeline["source_interval_s"],
        "coverage_gaps_s": timeline["coverage_gaps_s"],
        "input_sha256": {"timeline": digest(args.timeline),
                         "counter_gaps": digest(args.counter_gaps),
                         "visual_gaps": digest(args.visual_gaps) if args.visual_gaps else None,
                         "visual_parent_timeline": digest(args.visual_parent_timeline)
                         if args.visual_parent_timeline else None},
        "model_code_sha256": digest(ROOT / "prototype/beijing_gap_candidate_ledger.py"),
        "runner_sha256": digest(Path(__file__)),
        "evidence_row_count": len(rows),
        "evidence_kind_counts": dict(Counter(row["evidence_kind"] for row in rows)),
        "rows": rows,
        "complete_throw_sequence_verified": False,
        "simulation_ready": False,
        "limitations": [
            "Unknown route intervals remain coverage gaps even when counter or visual evidence exists inside them.",
            "A counter update can lag a delivery and a visual motion candidate can be a displaced stone.",
            "Nearby counter and visual evidence is a temporal association, not proven one-stone identity.",
            "Boundary transitions may duplicate supported events and are not distinct throw counts.",
            "No independent full-match event reference or complete post-throw board is available.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({"source": timeline["source_id"],
                      "rows": len(rows), "kinds": output["evidence_kind_counts"]}))


if __name__ == "__main__":
    main()
