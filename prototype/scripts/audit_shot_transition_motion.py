"""Join cut-separated cap motion to current/following broadcast shots."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256
from shot_context import shot_for_time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve first transition audit")
    review = json.loads((args.review / "manifest.json").read_text())
    candidates = json.loads(args.candidates.read_text())
    if review["source_sha256"] != candidates["source_sha256"] or review["source_interval_s"] != candidates["source_interval_s"]:
        parser.error("Review and cap candidates do not cover the same video span")
    shots = review["shots"]
    intervals = [row["interval_s"] for row in shots]
    by_shot = [[] for _ in shots]
    for candidate in candidates["motion_candidates"]:
        start, end = candidate["evidence_interval_s"]
        index = shot_for_time(intervals, (start + end) / 2)
        by_shot[index].append({"id": candidate["id"], "parent_id": candidate.get("parent_id"),
                               "colour": candidate["colour"],
                               "interval_s": [start, end],
                               "span_px": round(candidate["visual_track_span_px"], 2),
                               "point_count": len(candidate["visual_track_points"])})
    rows = []
    for index, shot in enumerate(shots):
        rows.append({"shot_id": shot["id"], "interval_s": shot["interval_s"],
                     "same_shot_candidates": by_shot[index],
                     "following_shot_id": shots[index + 1]["id"]
                     if index + 1 < len(shots) else None,
                     "following_shot_candidates": by_shot[index + 1]
                     if index + 1 < len(shots) else []})
    result = {
        "status": "development_shot_transition_cap_motion_audit",
        "source_id": candidates["source_id"], "source_sha256": candidates["source_sha256"],
        "source_interval_s": candidates["source_interval_s"],
        "shot_manifest_sha256": file_sha256(args.review / "manifest.json"),
        "candidates_sha256": file_sha256(args.candidates),
        "runner_sha256": file_sha256(__file__), "shots": rows,
        "limitations": [
            "Cap motion within a shot can be a player, camera pan, or displaced stone.",
            "A tracked cap in the following shot is not proven to be the delivered stone.",
            "The candidate generator excludes short and slow true tracks before this audit.",
        ],
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"shots": len(rows), "cap_candidates": len(candidates["motion_candidates"])}))


if __name__ == "__main__":
    main()
