"""Apply the frozen experimental 2024 split-screen passage confirmation rule."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256
from passage_confirmation import confirm_passages


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve prior candidate checks")
    source = json.loads(args.candidates.read_text())
    decisions = confirm_passages(source["events"])
    accepted = {item["id"] for item in decisions if item["status"] == "confirmed"}
    result = {
        "status": "same_layout_experimental_transfer_candidate",
        "source_id": source["source_id"],
        "source_sha256": source["source_sha256"],
        "source_interval_s": source["source_interval_s"],
        "input_sha256": file_sha256(args.candidates),
        "model_sha256": file_sha256(ROOT / "prototype/passage_confirmation.py"),
        "runner_sha256": file_sha256(__file__),
        "events": [event for event in source["events"] if event["id"] in accepted],
        "withheld_events": [event for event in source["events"] if event["id"] not in accepted],
        "decisions": decisions,
        "limitations": [
            "Thresholds were chosen after source review on two 2024 development intervals.",
            "Only the 2024 fixed split-screen layout is supported.",
            "Confirmation is not independent evidence of a stone or exact release time.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"confirmed": len(result["events"]),
                      "withheld": len(result["withheld_events"]) }))


if __name__ == "__main__":
    main()
