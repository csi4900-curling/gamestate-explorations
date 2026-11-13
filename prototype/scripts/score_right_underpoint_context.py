"""Score a below-track non-ice diagnostic on source-reviewed right prefixes."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
sys.path.insert(0, str(ROOT / "prototype/scripts"))
from right_track_underpoint_context import three_sample_underpoint
from score_right_track_ice_context import selected

UNDERPOINT_REVIEW_THRESHOLD = 0.25


def digest(path):
    result = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("video", "proposals", "review", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument(
        "--kind",
        choices=("bidirectional", "entry", "clip", "scotland_selected_entry"),
        required=True,
    )
    parser.add_argument("--recording", required=True)
    parser.add_argument("--source-offset", type=int, default=0)
    parser.add_argument("--fusion", type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    proposals = json.loads(args.proposals.read_text())
    review = json.loads(args.review.read_text())
    source_hash = digest(args.video)
    if proposals["source_sha256"] != source_hash:
        parser.error("Video and proposal sources differ")
    if args.kind == "clip":
        if (
            review["source_sha256"] != source_hash
            or review["probe_sha256"] != digest(args.proposals)
            or proposals["source_time_offset_s"] != args.source_offset
        ):
            parser.error("Clip source, review or offset differs")
        labels = {row["raw_track_id"]: row["source_prefix_class"] for row in review["rows"]}
        paths = proposals["directional_review_proposals"]
        if len(labels) != len(review["rows"]) or set(labels) != {
            row["raw_track_id"] for row in paths
        }:
            parser.error("Clip review must cover every proposal")
        paths = [(row, labels[row["raw_track_id"]]) for row in paths]
    elif args.kind == "scotland_selected_entry":
        if args.source_offset != 0 or args.fusion is None:
            parser.error("Scotland review requires fusion and zero source offset")
        fusion = json.loads(args.fusion.read_text())
        if (
            review["source_sha256"] != source_hash
            or fusion["source_sha256"] != source_hash
            or fusion["right_sha256"] != digest(args.proposals)
            or review["fusion_v2_sha256"] != digest(args.fusion)
        ):
            parser.error("Scotland source review lineage differs")
        labels = {
            row["right_raw_track_id"]: row["sampled_prefix_class"] for row in review["review"]
        }
        proposals_by_id = {row["raw_track_id"]: row for row in proposals["entry_review_proposals"]}
        if (
            len(labels) != len(review["review"])
            or len(proposals_by_id) != len(proposals["entry_review_proposals"])
            or not set(labels) <= set(proposals_by_id)
        ):
            parser.error("Invalid selected Scotland review")
        paths = [(proposals_by_id[raw_id], source_class) for raw_id, source_class in labels.items()]
    else:
        if args.source_offset != 0:
            parser.error("Un-offset probe requires source offset zero")
        if args.kind == "entry" and review["source_sha256"] != source_hash:
            parser.error("Entry source review differs")
        if args.kind == "bidirectional":
            source = next(
                (row for row in review["sources"] if row["recording"] == args.recording), None
            )
            if source is None or source["source_sha256"] != source_hash:
                parser.error("Bidirectional source review differs")
        paths = selected(proposals, review, args.kind, args.recording, digest(args.proposals))
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        parser.error("Cannot open source video")
    fps = cap.get(cv2.CAP_PROP_FPS)
    rows = []
    try:
        for proposal, source_class in paths:
            points = proposal["observed_prefix_points"]
            event_time = (
                proposal["entry_crossing"]["time_s"]
                if args.kind in ("entry", "scotland_selected_entry")
                else proposal["passage"]["time_s"]
            )
            chosen = [
                points[0],
                min(points, key=lambda point: abs(point["time_s"] - event_time)),
                points[-1],
            ]
            frames = []
            for point in chosen:
                local_time = point["time_s"] - args.source_offset
                cap.set(cv2.CAP_PROP_POS_FRAMES, round(local_time * fps))
                ok, frame = cap.read()
                if not ok:
                    raise RuntimeError(f"Could not decode source time {point['time_s']}")
                if frame.shape[:2] != (360, 640):
                    frame = cv2.resize(frame, (640, 360), interpolation=cv2.INTER_AREA)
                frames.append(frame)
            result = three_sample_underpoint(frames, chosen)
            fraction = result["median_underpoint_nonice_fraction"]
            rows.append(
                {
                    "raw_track_id": proposal["raw_track_id"],
                    "source_prefix_class": source_class,
                    "sample_source_times_s": [point["time_s"] for point in chosen],
                    **result,
                    "review_tier": (
                        "underpoint_unavailable"
                        if fraction is None
                        else "underpoint_cluttered_review"
                        if fraction > UNDERPOINT_REVIEW_THRESHOLD
                        else "underpoint_clear_review"
                    ),
                }
            )
    finally:
        cap.release()
    counts = Counter((row["source_prefix_class"], row["review_tier"]) for row in rows)
    result = {
        "status": "development_underpoint_review_cue_not_physical_stone_classifier",
        "source_sha256": source_hash,
        "recording": args.recording,
        "proposal_kind": args.kind,
        "proposals_sha256": digest(args.proposals),
        "source_review_sha256": digest(args.review),
        "feature_code_sha256": digest(ROOT / "prototype/right_track_underpoint_context.py"),
        "runner_sha256": digest(Path(__file__)),
        "sample_geometry_640x360": {"half_width": 20, "top_offset": 22, "bottom_offset": 60},
        "ice_hsv_rule": {"saturation_less_than": 90, "value_greater_than": 150},
        "nonice_review_threshold": UNDERPOINT_REVIEW_THRESHOLD,
        "counts_by_source_class_and_tier": {
            source_class: {
                tier: counts[source_class, tier]
                for tier in (
                    "underpoint_clear_review",
                    "underpoint_cluttered_review",
                    "underpoint_unavailable",
                )
            }
            for source_class in sorted({row["source_prefix_class"] for row in rows})
        },
        "rows": rows,
        "limitations": [
            "Band geometry and threshold were chosen after inspecting Slovakia failures.",
            "Same-agent source classes are not independent physical throw labels.",
            "Ice markings, equipment and overlap can clutter the band under a stone.",
            "A clear band cannot by itself establish stone identity.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"rows": len(rows), "counts": result["counts_by_source_class_and_tier"]}))


if __name__ == "__main__":
    main()
