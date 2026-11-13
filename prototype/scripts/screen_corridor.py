"""Preserve bidirectional candidates and screen by a declared camera corridor."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256
from passage_corridor import screen_corridor


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--center-x-px", type=float, required=True)
    parser.add_argument("--half-width-px", type=float, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    source = json.loads(args.events.read_text())
    screened = screen_corridor(
        source["events"], center_x_px=args.center_x_px, half_width_px=args.half_width_px
    )
    accepted = {e["id"] for e in screened if e["status"] == "ice_corridor_candidate"}
    result = {
        "status": "development_tuned_layout_screen",
        "source_id": source["source_id"],
        "source_sha256": source["source_sha256"],
        "source_interval_s": source["source_interval_s"],
        "input_sha256": file_sha256(args.events),
        "model_sha256": file_sha256(ROOT / "prototype/passage_corridor.py"),
        "runner_sha256": file_sha256(__file__),
        "geometry": {
            "center_x_px": args.center_x_px,
            "half_width_px": args.half_width_px,
            "coordinates": "normalized 640x360 full frame; left 320px panel",
        },
        "events": [e for e in source["events"] if e["id"] in accepted],
        "withheld_events": [e for e in source["events"] if e["id"] not in accepted],
        "screened_events": screened,
        "limitations": [
            "The geometry was selected after inspecting same-layout Canada–Italy disagreements.",
            "Off-corridor events are preserved as candidates, not silently deleted.",
            "No independent performance or camera-family generalization claim follows.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps({"accepted": len(result["events"]), "withheld": len(result["withheld_events"])})
    )


if __name__ == "__main__":
    main()
