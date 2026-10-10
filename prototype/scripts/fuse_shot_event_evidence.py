"""Fuse frozen shot, motion, and delayed-counter evidence for an interval."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256
from shot_event_fusion import fuse_shot_events


def score(rows):
    tp = sum(row["label"] == 1 and row["predicted"] == 1 for row in rows)
    fp = sum(row["label"] == 0 and row["predicted"] == 1 for row in rows)
    fn = sum(row["label"] == 1 and row["predicted"] == 0 for row in rows)
    tn = sum(row["label"] == 0 and row["predicted"] == 0 for row in rows)
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "precision": tp / (tp + fp) if tp + fp else None,
            "recall": tp / (tp + fn) if tp + fn else None,
            "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origins", type=Path, required=True)
    parser.add_argument("--two-shot", type=Path, required=True)
    parser.add_argument("--counter-alignment", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve first fusion result")
    origins = json.loads(args.origins.read_text())
    two_shot = json.loads(args.two_shot.read_text())
    counter = json.loads(args.counter_alignment.read_text())
    digest = file_sha256(args.origins)
    for source in (two_shot, counter):
        if (source["source_sha256"] != origins["source_sha256"] or
                source["source_interval_s"] != origins["source_interval_s"]):
            parser.error("Evidence sources do not cover the same interval")
    if two_shot["origins_sha256"] != digest or counter["shot_score_sha256"] != digest:
        parser.error("Evidence sources do not derive from these origin predictions")
    fusion = fuse_shot_events(origins["rows"], two_shot["decisions"], counter["rows"],
                              allow_rescue="learned" in two_shot["motion_sha256"])
    selected = {row["shot_id"] for row in fusion["events"]}
    resolved = [{**row, "predicted": int(row["shot_id"] in selected)}
                for row in origins["rows"] if row["label"] in (0, 1)]
    result = {
        "status": "postscore_development_shot_evidence_fusion_not_full_event_detection",
        "source_sha256": origins["source_sha256"],
        "source_interval_s": origins["source_interval_s"],
        "origins_sha256": digest,
        "two_shot_sha256": file_sha256(args.two_shot),
        "counter_alignment_sha256": file_sha256(args.counter_alignment),
        "fusion_code_sha256": file_sha256(ROOT / "prototype/shot_event_fusion.py"),
        "runner_sha256": file_sha256(__file__),
        "candidate_count": len(fusion["events"]),
        "resolved_shot_score": score(resolved) if resolved else None,
        **fusion,
        "limitations": [
            "Postscore development fusion on exposed intervals; selection and rescue rules were shaped by prior errors.",
            "Agent-authored shot labels are not exhaustive independent throw-event ground truth.",
            "Delivery windows bound broadcast shots, not physical release or full stone travel.",
            "Counter changes can be unreadable, delayed, or absent; unassociated changes remain unresolved.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"candidates": result["candidate_count"],
                      "shot_score": result["resolved_shot_score"]}))


if __name__ == "__main__":
    main()
