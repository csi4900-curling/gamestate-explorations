"""Measure ice-like support beneath reviewed Latvia high-res image paths."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
from statistics import median
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from highres_underpoint_context import (  # noqa: E402
    review_tier,
    underpoint_nonice_fraction,
)

BASE = ROOT / "validation/throw-event-benchmark/canada-latvia-2024"
LANE = ROOT / "validation/throw-event-benchmark/layout-router/full-2024-coverage/latvia24-full-v1"
VIDEO = BASE / "source-1080p-5670-6670.mp4"
JOIN = BASE / "end6-cross-resolution-body-cap-development.json"
RED = LANE / "end6-highres-red-full-transfer-development.json"
NEGATIVE = BASE / "end6-unmatched-highres-red-source.json"
OUT = BASE / "end6-highres-underpoint-context-development.json"


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def main():
    if OUT.exists():
        raise ValueError("Underpoint audit already exists")
    join, red, negative = (json.loads(p.read_text()) for p in (JOIN, RED, NEGATIVE))
    source_hash = digest(VIDEO)
    if (
        source_hash != join["highres_source_sha256"]
        or source_hash != red["source_video_sha256"]
        or source_hash != negative["source_video_sha256"]
        or negative["cross_resolution_join_sha256"] != digest(JOIN)
        or negative["red_path_sha256"] != digest(RED)
    ):
        raise ValueError("High-resolution path source lineage differs")
    selected = []
    for item in join["rows"]:
        if item["source_prefix_class"] != "moving_stone_pixels":
            continue
        compatible = item["compatible_highres_paths"]
        if len(compatible) != 1:
            raise ValueError("Reviewed positive lacks unique high-res path")
        selected.append(
            {
                "path_id": item["right_proposal_id"],
                "source_pixel_class": "moving_stone_pixels",
                "sample_points": [
                    {"time_s": p["time_s"], "center_1080p_px": p["center_1080p_px"]}
                    for p in compatible[0]["highres_handle_supported_moving_points"]
                ],
            }
        )
    red_paths = {p["diagnostic_path_id"]: p for p in red["red_supported_image_paths"]}
    for item in negative["rows"]:
        path = red_paths[item["highres_path_id"]]
        selected.append(
            {
                "path_id": item["highres_path_id"],
                "source_pixel_class": item["reviewed_marked_pixel_class"],
                "sample_points": [
                    {"time_s": p["time_s"], "center_1080p_px": p["center_1080p_px"]}
                    for p in path["points"]
                ],
            }
        )
    capture = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not capture.isOpened():
        raise ValueError("Source unreadable")
    fps = capture.get(cv2.CAP_PROP_FPS)
    rows = []
    try:
        for item in selected:
            scores = []
            for point in item["sample_points"]:
                index = round((point["time_s"] - 5670) * fps)
                capture.set(cv2.CAP_PROP_POS_FRAMES, index)
                ok, frame = capture.read()
                if not ok:
                    raise ValueError(f"Frame {index} unreadable")
                value = underpoint_nonice_fraction(frame, point["center_1080p_px"])
                scores.append(
                    {
                        "source_time_s": point["time_s"],
                        "decoded_frame_index": index,
                        "center_1080p_px": point["center_1080p_px"],
                        "underpoint_nonice_fraction": (None if value is None else round(value, 4)),
                    }
                )
            available = [
                s["underpoint_nonice_fraction"]
                for s in scores
                if s["underpoint_nonice_fraction"] is not None
            ]
            middle = round(median(available), 4) if available else None
            rows.append(
                {
                    "path_id": item["path_id"],
                    "source_pixel_class": item["source_pixel_class"],
                    "available_sample_count": len(available),
                    "median_underpoint_nonice_fraction": middle,
                    "review_tier": review_tier(middle),
                    "samples": scores,
                    "physical_throw_verified": False,
                }
            )
    finally:
        capture.release()
    counts = Counter((r["source_pixel_class"], r["review_tier"]) for r in rows)
    payload = {
        "status": "postreview_highres_underpoint_development_diagnostic_not_throw_truth",
        "source_video_sha256": source_hash,
        "join_sha256": digest(JOIN),
        "red_paths_sha256": digest(RED),
        "negative_source_packet_sha256": digest(NEGATIVE),
        "feature_code_sha256": digest(ROOT / "prototype/highres_underpoint_context.py"),
        "runner_sha256": digest(Path(__file__)),
        "method": "Existing 360p underpoint HSV and 20/22/60 px band scaled exactly 3x to full 1080p; reviewed moving-prefix body points and all three unmatched source-reviewed person paths; descriptive 0.05/0.25 review tiers, no hard rejection.",
        "path_count": len(rows),
        "tier_counts_by_source_pixel_class": {
            cls: {
                tier: counts[(cls, tier)]
                for tier in (
                    "clear_context_review",
                    "ambiguous_context_review",
                    "cluttered_context_review",
                    "context_unavailable",
                )
            }
            for cls in sorted({r["source_pixel_class"] for r in rows})
        },
        "rows": rows,
        "limitations": [
            "Sample class labels were assigned by the detector developer after viewing the same source; these are not independent physical throw labels.",
            "A white jersey or another bright foreground object can look ice-like in HSV; clear context is not stone proof.",
            "The 0.05 ambiguity boundary is a postreview diagnostic choice. The 0.25 clutter threshold came from the earlier 360p context screen.",
            "Only selected path points are scored; no full-video precision, recall or F1 follows.",
        ],
    }
    OUT.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps({"paths": len(rows), "tiers": payload["tier_counts_by_source_pixel_class"]}))


if __name__ == "__main__":
    main()
