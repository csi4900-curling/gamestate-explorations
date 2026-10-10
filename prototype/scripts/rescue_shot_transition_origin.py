"""Postscore weak-origin rescue from a preserved two-shot decision."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256
from scripts.score_shot_origin_transfer import score
from shot_transition_rescue import rescue_weak_origins


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origins", type=Path, required=True)
    parser.add_argument("--two-shot", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve first rescue result")
    origins = json.loads(args.origins.read_text())
    two_shot = json.loads(args.two_shot.read_text())
    if (two_shot["origins_sha256"] != file_sha256(args.origins)
            or two_shot["source_sha256"] != origins["source_sha256"]):
        parser.error("Two-shot decision does not derive from these origin predictions")
    if "learned" not in two_shot["motion_sha256"]:
        parser.error("Two-channel motion is required for rescue")
    decisions = rescue_weak_origins(origins["rows"], two_shot["decisions"])
    by_id = {row["shot_id"]: row for row in decisions}
    evaluated = [{**row, "predicted": int(by_id[row["shot_id"]]["status"]
                                   in ("corroborated_candidate", "rescued_candidate"))}
                 for row in origins["rows"] if row["label"] in (0, 1)]
    result = {
        "status": "postscore_development_weak_origin_rescue_not_confirmed_events",
        "source_sha256": origins["source_sha256"],
        "source_interval_s": origins["source_interval_s"],
        "origins_sha256": file_sha256(args.origins),
        "two_shot_sha256": file_sha256(args.two_shot),
        "model_sha256": file_sha256(ROOT / "prototype/shot_transition_rescue.py"),
        "runner_sha256": file_sha256(__file__),
        "minimum_origin_probability": 0.2,
        "decisions": decisions,
        "resolved_shot_score": score(evaluated),
        "limitations": [
            "This rescue threshold was designed after the red miss in this same interval.",
            "Both motion channels share frames and colour segmentation, so agreement is not independent proof.",
            "No full-video event-F1, release-time, or physical stone identity claim follows.",
        ],
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result["resolved_shot_score"], indent=2))


if __name__ == "__main__":
    main()
