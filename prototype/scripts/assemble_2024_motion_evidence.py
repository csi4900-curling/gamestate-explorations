"""Assemble directional Canada–China motion observations from development audits."""

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256  # noqa: E402
from throw_motion_evidence import combine_directional_event  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--primary", type=Path, required=True)
    parser.add_argument("--supplement", type=Path,
                        help="Denser audit for an event missing in the primary sample")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Motion evidence artifact already exists")
    primary = json.loads(args.primary.read_text())
    supplement = json.loads(args.supplement.read_text()) if args.supplement else None
    overrides = {}
    if supplement is not None:
        if supplement["source_video_sha256"] != primary["source_video_sha256"] or (
                supplement["reference_sha256"] != primary["reference_sha256"]):
            parser.error("Supplement source or reference differs")
        for row in supplement["rows"]:
            overrides[row["event_id"]] = row["left_reverse_selection"]
    rows = [combine_directional_event(row, overrides.get(row["event_id"]))
            for row in primary["rows"]]
    summary = dict(Counter(row["status"] for row in rows))
    result = {
        "status": "development_directional_motion_evidence_not_event_validation_or_game_state",
        "source_video_sha256": primary["source_video_sha256"],
        "reference_sha256": primary["reference_sha256"],
        "primary_sha256": file_sha256(args.primary),
        "supplement_sha256": file_sha256(args.supplement) if args.supplement else None,
        "assembler_sha256": file_sha256(__file__),
        "combiner_sha256": file_sha256(ROOT / "prototype/throw_motion_evidence.py"),
        "reference_window_count": len(rows),
        "status_counts": summary,
        "rows": rows,
        "limitations": [
            "This conditions on agent-authored source-only windows and their colours; it is not full-video event recall or precision.",
            "Motion selectors were developed after inspecting this recording; these counts are postscore development coverage, not an independent test.",
            "The C03 supplement uses denser temporal sampling than the other windows.",
            "An observed path may stop at identity ambiguity, occlusion, or the reference-window boundary; none has a validated release time or complete settled board.",
            "Conditional projected positions are not measured stone centres or simulation-ready game state.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(summary)


if __name__ == "__main__":
    main()
