"""Score visual candidates against frozen, overlapping counter proxy windows."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256
from counter_concordance import concordance


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--screen", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve first score")
    raw = json.loads(args.raw.read_text())
    screen = json.loads(args.screen.read_text())
    reference = json.loads(args.reference.read_text())
    if any(row["source_sha256"] != raw["source_sha256"]
           or row["source_interval_s"] != raw["source_interval_s"]
           for row in (screen, reference)):
        parser.error("Source or interval mismatch")
    if screen["input_sha256"] != file_sha256(args.raw):
        parser.error("Screen does not derive from raw candidates")
    if reference["reference_method"] != "high_visibility_broadcast_counter_proxy":
        parser.error("Reference is not a counter proxy")
    result = {
        "status": "weak_counter_visual_concordance_not_event_f1",
        "source_id": raw["source_id"],
        "source_sha256": raw["source_sha256"],
        "source_interval_s": raw["source_interval_s"],
        "raw_sha256": file_sha256(args.raw),
        "screen_sha256": file_sha256(args.screen),
        "reference_sha256": file_sha256(args.reference),
        "matcher_sha256": file_sha256(ROOT / "prototype/counter_concordance.py"),
        "runner_sha256": file_sha256(__file__),
        "raw": concordance(raw["motion_candidates"], reference["events"]),
        "screen": concordance(screen["corroborated_candidates"], reference["events"]),
        "limitations": [
            "Counter proxy windows overlap and were expanded by 15 seconds on either side.",
            "Visual/counter agreement is not independent event precision, recall or F1.",
            "An unmatched visual candidate may be a true throw despite no counter match.",
            "A matched candidate may be a moving non-delivered stone inside a generous counter window.",
        ],
    }
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({name: {key: result[name][key] for key in
                              ("counter_count", "candidate_count", "temporal_match_count",
                               "colour_match_count")}
                      for name in ("raw", "screen")}, indent=2))


if __name__ == "__main__":
    main()
