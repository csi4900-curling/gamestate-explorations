"""Score ice-context diagnostics on every unreviewed full-match right path."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from right_context_tier import context_tier
from right_track_ice_context import three_sample_context
from right_track_underpoint_context import three_sample_underpoint


def digest(path):
    result = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument(
        "--run", nargs=2, action="append", metavar=("RUN_ID", "PROBE"), required=True
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    inventory = json.loads(args.inventory.read_text())
    source_hash = digest(args.video)
    if inventory["source_sha256"] != source_hash:
        parser.error("Inventory and video source differ")
    probes = {}
    for run_id, path_str in args.run:
        path = Path(path_str)
        probe = json.loads(path.read_text())
        if (
            run_id in probes
            or probe["source_sha256"] != source_hash
            or inventory["right_probe_sha256_by_run"].get(run_id) != digest(path)
        ):
            parser.error(f"{run_id} probe lineage differs")
        ids = {row["raw_track_id"]: row for row in probe["directional_review_proposals"]}
        if len(ids) != len(probe["directional_review_proposals"]):
            parser.error(f"{run_id} duplicate raw IDs")
        probes[run_id] = ids
    if set(probes) != set(inventory["right_probe_sha256_by_run"]):
        parser.error("One probe per inventory run required")
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        parser.error("Cannot open source video")
    fps = cap.get(cv2.CAP_PROP_FPS)
    rows = []
    try:
        for item in inventory["rows"]:
            proposal = probes[item["run_id"]][item["raw_track_id"]]
            points = proposal["observed_prefix_points"]
            passage_t = proposal["passage"]["time_s"]
            chosen = [
                points[0],
                min(points, key=lambda x: abs(x["time_s"] - passage_t)),
                points[-1],
            ]
            frames = []
            for point in chosen:
                cap.set(cv2.CAP_PROP_POS_FRAMES, round(point["time_s"] * fps))
                ok, frame = cap.read()
                if not ok:
                    raise RuntimeError(f"Could not decode {point['time_s']}")
                frames.append(cv2.resize(frame, (640, 360), interpolation=cv2.INTER_AREA))
            ring = three_sample_context(frames, chosen)
            under = three_sample_underpoint(frames, chosen)
            ring_value = ring["median_nonice_ring_fraction"]
            under_value = under["median_underpoint_nonice_fraction"]
            rows.append(
                {
                    "proposal_id": item["proposal_id"],
                    "temporal_status": item["temporal_status"],
                    "sample_source_times_s": [p["time_s"] for p in chosen],
                    "median_nonice_ring_fraction": ring_value,
                    "median_underpoint_nonice_fraction": under_value,
                    "context_tier": context_tier(ring_value, under_value),
                    "source_visible_class": None,
                    "physical_throw_identity_verified": False,
                }
            )
    finally:
        cap.release()
    counts = Counter((row["temporal_status"], row["context_tier"]) for row in rows)
    result = {
        "status": "unreviewed_full_match_right_context_diagnostic_not_throw_classifier",
        "source_sha256": source_hash,
        "inventory_sha256": digest(args.inventory),
        "right_probe_sha256_by_run": inventory["right_probe_sha256_by_run"],
        "ring_feature_sha256": digest(ROOT / "prototype/right_track_ice_context.py"),
        "underpoint_feature_sha256": digest(ROOT / "prototype/right_track_underpoint_context.py"),
        "tier_code_sha256": digest(ROOT / "prototype/right_context_tier.py"),
        "runner_sha256": digest(Path(__file__)),
        "nonice_threshold": 0.25,
        "proposal_count": len(rows),
        "counts_by_temporal_status_and_context": {
            status: {
                tier: counts[status, tier]
                for tier in (
                    "clear_context_review",
                    "context_cluttered_review",
                    "context_unavailable_review",
                )
            }
            for status in sorted({row["temporal_status"] for row in rows})
        },
        "rows": rows,
        "limitations": [
            "No source-visible object labels were used or inferred for all paths.",
            "Clear context can include stone handling and does not imply a throw.",
            "A cluttered score can reflect occlusion around a real stone.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps({"rows": len(rows), "counts": result["counts_by_temporal_status_and_context"]})
    )


if __name__ == "__main__":
    main()
