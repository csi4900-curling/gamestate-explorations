"""Select a provisional same-view moving-stone run from a dense proposal audit."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256  # noqa: E402
from stone_proposal_path import select_single_colour_motion_run  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proposals", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--event-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Motion-path artifact already exists")
    proposals = json.loads(args.proposals.read_text())
    reference = json.loads(args.reference.read_text())
    event = next((e for e in reference["events"] if e["id"] == args.event_id), None)
    if event is None:
        parser.error("Unknown event ID")
    rows = [r for r in proposals["rows"] if r["reference_event_id"] == args.event_id]
    if not rows:
        parser.error("No proposal rows for event")
    selection = select_single_colour_motion_run(rows, event["colour"])
    result = {"status": "development_same_view_motion_path_not_stone_identity_validation",
              "event_id": args.event_id,
              "reference_colour": event["colour"],
              "source_video_sha256": proposals["source_video_sha256"],
              "proposals_sha256": file_sha256(args.proposals),
              "reference_sha256": file_sha256(args.reference),
              "selector_sha256": file_sha256(ROOT / "prototype/stone_proposal_path.py"),
              "runner_sha256": file_sha256(__file__),
              "selection": selection,
              "limitations": [
                  "The coarse source-only reference supplies a colour and window, not a release time.",
                  "One same-colour proposal per frame is provisional association, not independently verified stone identity.",
                  "A track of conditional projected centres is not physical metric validation.",
                  "No cross-view association, collision resolution, settled board, or simulator output is inferred.",
              ]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print({key: value for key, value in selection.items() if key != "path"})


if __name__ == "__main__":
    main()
