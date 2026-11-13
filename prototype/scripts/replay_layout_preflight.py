"""Replay saved layout samples through current rules without decoding video."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from layout_preflight import split_2024_signature, summarize_evidence


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve first replay")
    source = json.loads(args.preflight.read_text())
    if not source.get("samples") or not source.get("chunks"):
        parser.error("Input preflight has no saved samples or chunks")
    start, end = source["source_interval_s"]
    refreshed = [
        {
            **row,
            "split_2024_signature": split_2024_signature(
                row["left_pale_fraction"], row["left_bright_fraction"], row["right_blue_fraction"]
            ),
        }
        for row in source["samples"]
    ]
    route = summarize_evidence(refreshed, start, end, chunk_s=source["layout_chunk_s"])
    result = {
        "status": "postscore_development_layout_replay_not_event_validation",
        "source_id": source["source_id"],
        "source_sha256": source["source_sha256"],
        "source_interval_s": source["source_interval_s"],
        "layout_chunk_s": source["layout_chunk_s"],
        "input_preflight_sha256": digest(args.preflight),
        "layout_code_sha256": digest(ROOT / "prototype/layout_preflight.py"),
        "runner_sha256": digest(Path(__file__)),
        "original_layout": source["layout"],
        "original_coverage_gaps_s": source["coverage_gaps_s"],
        "recomputed_split_signature_count": sum(row["split_2024_signature"] for row in refreshed),
        **route,
        "limitations": [
            "Replaying sparse saved frames is a routing diagnostic, not continuous camera coverage.",
            "No throw detector or event reference was used; no event precision or recall follows.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    original_gap_s = sum(hi - lo for lo, hi in source["coverage_gaps_s"])
    revised_gap_s = sum(hi - lo for lo, hi in route["coverage_gaps_s"])
    print(
        json.dumps(
            {
                "source_id": source["source_id"],
                "original_unknown_s": original_gap_s,
                "revised_unknown_s": revised_gap_s,
            }
        )
    )


if __name__ == "__main__":
    main()
