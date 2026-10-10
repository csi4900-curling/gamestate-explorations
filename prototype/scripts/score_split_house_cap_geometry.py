"""Score each pre/post cap relative to source-derived right-house paint."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from split_house_cap_geometry import normalized_house_distance, house_location_tier

NEAR_HOUSE_DISTANCE = 1.4


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--context", type=Path, required=True)
    parser.add_argument(
        "--reference", nargs=2, action="append", required=True, metavar=("RUN_ID", "REFERENCE_JSON")
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    context = json.loads(args.context.read_text())
    refs = {}
    paths = {}
    for run_id, raw_path in args.reference:
        path = Path(raw_path)
        item = json.loads(path.read_text())
        if (
            run_id in refs
            or item["run_id"] != run_id
            or item["source_sha256"] != context["source_sha256"]
        ):
            parser.error("Duplicate or mismatched house reference")
        refs[run_id] = item["temporal_median_house_ellipse"]
        paths[run_id] = path
    rows = []
    for item in context["rows"]:
        run_id = item["candidate_id"].split(":", 1)[1].split("-", 1)[0]
        if run_id not in refs:
            parser.error("Cap belongs to a run without a house reference")
        distance = normalized_house_distance(refs[run_id], item["pixel_center"])
        rows.append(
            {
                "candidate_id": item["candidate_id"],
                "run_id": run_id,
                "phase": item["phase"],
                "local_observation_id": item["local_observation_id"],
                "colour": item["colour"],
                "pixel_center": item["pixel_center"],
                "normalized_paint_ellipse_distance": round(distance, 4)
                if distance is not None
                else None,
                "house_location_tier": house_location_tier(
                    distance, near_distance=NEAR_HOUSE_DISTANCE
                ),
                "ice_context_tier": item["context_tier"],
                "physical_stone_identity_verified": False,
            }
        )
    counts = Counter((r["house_location_tier"], r["ice_context_tier"]) for r in rows)
    output = {
        "status": "source_derived_house_image_location_review_not_physical_board_geometry",
        "source_sha256": context["source_sha256"],
        "context_sha256": digest(args.context),
        "house_reference_sha256_by_run": {run: digest(path) for run, path in paths.items()},
        "model_code_sha256": digest(ROOT / "prototype/split_house_cap_geometry.py"),
        "runner_sha256": digest(Path(__file__)),
        "near_house_normalized_distance": NEAR_HOUSE_DISTANCE,
        "cap_count": len(rows),
        "tier_counts": {
            house: {
                ice: counts[house, ice]
                for ice in (
                    "clear_context_review",
                    "context_cluttered_review",
                    "context_unavailable_review",
                )
            }
            for house in (
                "near_painted_house_review",
                "outside_painted_house_review",
                "house_geometry_unavailable_review",
            )
        },
        "rows": rows,
        "limitations": [
            "The 1.4-radius review band was chosen after exposed 2024 source probing.",
            "The fitted paint ellipse represents the scoring house, not guards or all playable ice.",
            "A cap near the painted house can still be a player, equipment or handled stone.",
            "Image ellipse distance is not a validated physical coordinate or simulation input.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({"caps": len(rows), "tiers": output["tier_counts"]}))


if __name__ == "__main__":
    main()
