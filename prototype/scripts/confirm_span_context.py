"""Confirm compact stone-like passages while retaining all withheld evidence."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256
from span_context_confirmation import confirm_span_context


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--motion", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve prior checks")
    source = json.loads(args.candidates.read_text())
    motion = json.loads(args.motion.read_text())
    if motion["input_sha256"] != file_sha256(args.candidates):
        parser.error("Motion measurements do not match candidate artifact")
    decisions = confirm_span_context(source["events"], motion["rows"])
    accepted = {item["id"] for item in decisions if item["status"] == "confirmed"}
    result = {
        "status": "development_fitted_2024_split_screen_candidate",
        "source_id": source["source_id"],
        "source_sha256": source["source_sha256"],
        "source_interval_s": source["source_interval_s"],
        "input_sha256": file_sha256(args.candidates),
        "motion_sha256": file_sha256(args.motion),
        "model_sha256": file_sha256(ROOT / "prototype/span_context_confirmation.py"),
        "runner_sha256": file_sha256(__file__),
        "events": [event for event in source["events"] if event["id"] in accepted],
        "withheld_events": [event for event in source["events"] if event["id"] not in accepted],
        "decisions": decisions,
        "limitations": [
            "Motion-area cutoff was chosen after observing three 2024 development recordings.",
            "The 2024 fixed split-screen left panel is the only supported camera layout.",
            "Observed passage time is a track midpoint, not exact release time.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps({"confirmed": len(result["events"]), "withheld": len(result["withheld_events"])})
    )


if __name__ == "__main__":
    main()
