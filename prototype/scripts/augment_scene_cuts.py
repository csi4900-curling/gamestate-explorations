"""Write an experimental full-source cut timeline from isolated edit proposals."""

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from augmented_scene_cuts import merge_cut_evidence  # noqa: E402
from cache_contract import file_sha256  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hard-cuts", required=True, type=Path)
    parser.add_argument("--edit-audit", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Augmented cut artifact already exists")
    hard = json.loads(args.hard_cuts.read_text())
    edits = json.loads(args.edit_audit.read_text())
    if hard["source_sha256"] != edits["source_sha256"] or (
        len(edits["rows"]) != sum(edits["counts"].values())
    ):
        raise ValueError("Edit audit does not match hard-cut source or counts")
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    if hard["source_sha256"] == reserved["source_sha256"]:
        raise ValueError("Reserved source cannot be used for development")
    cuts = merge_cut_evidence(hard["cuts"], edits["rows"], *hard["source_interval_s"])
    result = {
        "status": "development_augmented_camera_shot_timeline_not_verified_cuts",
        "source_id": hard["source_id"],
        "source_sha256": hard["source_sha256"],
        "source_interval_s": hard["source_interval_s"],
        "hard_cuts_sha256": file_sha256(args.hard_cuts),
        "edit_audit_sha256": file_sha256(args.edit_audit),
        "merge_code_sha256": file_sha256(ROOT / "prototype/augmented_scene_cuts.py"),
        "runner_sha256": file_sha256(__file__),
        "sample_rate_hz": hard["sample_rate_hz"],
        "cut_count": len(cuts),
        "cut_origin_counts": dict(Counter(row["cut_origin"] for row in cuts)),
        "cuts": cuts,
        "limitations": [
            "Additional split points are isolated image-change candidates, not independently verified camera cuts.",
            "A false split can break a real stone track or create a spurious origin candidate.",
            "This is a separate development timeline; the frozen first-pass hard cuts and events remain unchanged.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(result["cut_origin_counts"])


if __name__ == "__main__":
    main()
