"""Attach source-observed broadcast end displays to a provisional state handoff."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256  # noqa: E402
from display_context_handoff import attach_display_context  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--handoff", type=Path, required=True)
    parser.add_argument("--display-context", type=Path, required=True)
    parser.add_argument("--corridor", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Augmented handoff already exists")
    handoff = json.loads(args.handoff.read_text())
    context = json.loads(args.display_context.read_text())
    corridor = json.loads(args.corridor.read_text())
    if (
        handoff["source_id"] != context["source_id"]
        or handoff["source_sha256"] != context["source_sha256"]
        or handoff["source_interval_s"] != context["source_interval_s"]
        or corridor["source_id"] != context["source_id"]
        or corridor["source_interval_s"] != context["source_interval_s"]
        or corridor["source_sha256"] != context["source_sha256"]
        or file_sha256(args.corridor) != handoff["input_sha256"]["candidates"]
        or corridor["input_sha256"] != context["raw_sha256"]
    ):
        parser.error("Handoff and display context provenance differs")
    joined = attach_display_context(handoff, context)
    output = {
        **handoff,
        "status": "provisional_video_evidence_with_broadcast_display_context_not_complete_game_state",
        "upstream_handoff_sha256": file_sha256(args.handoff),
        "display_context_sha256": file_sha256(args.display_context),
        "display_join_code_sha256": file_sha256(ROOT / "prototype/display_context_handoff.py"),
        "display_join_runner_sha256": file_sha256(Path(__file__)),
        "timeline": joined,
        "limitations": handoff["limitations"]
        + [
            "Broadcast displayed ends are observational context, not physical end assignments.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print(len(joined))


if __name__ == "__main__":
    main()
