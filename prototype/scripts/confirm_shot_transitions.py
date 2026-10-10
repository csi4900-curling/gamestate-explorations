"""Apply two-channel adjacent-shot motion to frozen origin predictions."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256
from scripts.score_shot_origin_transfer import score
from shot_transition_confirmation import confirm_shot_transitions


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origins", type=Path, required=True)
    parser.add_argument("--cap-motion", type=Path, required=True)
    parser.add_argument("--learned-motion", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve first decision")
    origins = json.loads(args.origins.read_text())
    audits = {"cap": json.loads(args.cap_motion.read_text())}
    if args.learned_motion:
        audits["learned"] = json.loads(args.learned_motion.read_text())
    if any(
        audit["source_sha256"] != origins["source_sha256"]
        or audit["source_interval_s"] != origins["source_interval_s"]
        for audit in audits.values()
    ):
        parser.error("Origin predictions and motion audits differ in source or interval")
    decisions = confirm_shot_transitions(
        origins["rows"], {channel: audit["shots"] for channel, audit in audits.items()}
    )
    by_id = {row["shot_id"]: row for row in decisions}
    evaluated = [
        {**row, "predicted": int(by_id[row["shot_id"]]["status"] == "corroborated_candidate")}
        for row in origins["rows"]
        if row["label"] in (0, 1)
    ]
    result = {
        "status": "development_two_shot_motion_corroboration_not_confirmed_events",
        "source_sha256": origins["source_sha256"],
        "source_interval_s": origins["source_interval_s"],
        "origins_sha256": file_sha256(args.origins),
        "motion_sha256": {
            "cap": file_sha256(args.cap_motion),
            **({"learned": file_sha256(args.learned_motion)} if args.learned_motion else {}),
        },
        "model_sha256": file_sha256(ROOT / "prototype/shot_transition_confirmation.py"),
        "runner_sha256": file_sha256(__file__),
        "decisions": decisions,
        "resolved_shot_score": score(evaluated),
        "limitations": [
            "Source labels are agent-authored, not independent event ground truth.",
            "Two colour tracks across adjacent shots are temporal corroboration, not a verified stone identity link.",
            "The two proposal channels share frames and colour segmentation; they are not independent detectors.",
            "No exact release time, physical throw boundary, or full-video event F1 is established.",
        ],
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result["resolved_shot_score"], indent=2))


if __name__ == "__main__":
    main()
