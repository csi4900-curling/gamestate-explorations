"""Audit frozen Czech camera registration on Latvia held/quiet body paths."""

from collections import Counter
from hashlib import sha256
import json
import math
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from split_panel_camera_registration import (  # noqa: E402
    camera_relative_pair,
    panel_for_pixel,
    panel_pixel,
    resize_panel,
)

BASE = ROOT / "validation/throw-event-benchmark/canada-latvia-2024"
LANE = ROOT / "validation/throw-event-benchmark/layout-router/full-2024-coverage/latvia24-full-v1"
CZECH = ROOT / "validation/throw-event-benchmark/canada-czech-2024"
VIDEO = BASE / "source-1080p-5670-6670.mp4"
JOIN = BASE / "end6-cross-resolution-body-cap-development.json"
YELLOW = LANE / "end6-highres-body-handle-screen-development.json"
RED = LANE / "end6-highres-red-full-transfer-development.json"
FROZEN = BASE / "end6-split-panel-registration-czech-rule-transfer-development.json"
OUTPUT = BASE / "end6-split-panel-registration-held-path-controls-development.json"
SOURCE_OFFSET_S = 5670


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def main():
    if OUTPUT.exists():
        raise ValueError("Latvia quiet-control transfer already exists")
    join, yellow, red, frozen = (json.loads(p.read_text()) for p in (JOIN, YELLOW, RED, FROZEN))
    source_hash = digest(VIDEO)
    code_hash = digest(ROOT / "prototype/split_panel_camera_registration.py")
    if (
        source_hash != join["highres_source_sha256"]
        or source_hash != yellow["blind_video_sha256"]
        or source_hash != red["source_video_sha256"]
        or source_hash != frozen["source_video_sha256"]
        or code_hash != frozen["registration_code_sha256"]
        or frozen["join_sha256"] != digest(JOIN)
    ):
        raise ValueError("Latvia quiet source or Czech rule lineage differs")
    path_by_key = {("yellow", p["diagnostic_path_id"]): p for p in yellow["supported_image_paths"]}
    path_by_key.update(
        {("red", p["diagnostic_path_id"]): p for p in red["red_supported_image_paths"]}
    )
    cap = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        raise ValueError("Latvia high-resolution video unreadable")
    fps = cap.get(cv2.CAP_PROP_FPS)
    rows = []
    try:
        for item in join["rows"]:
            if item["source_prefix_class"] != "moving_stone_pixels":
                continue
            compatible = item["compatible_highres_paths"]
            if len(compatible) != 1:
                raise ValueError("Reviewed stone lacks unique high-res path")
            key = (item["colour_claim"], compatible[0]["highres_path_id"])
            path = path_by_key[key]
            quiet_end = item["observed_motion_onset"]["quiet_end_time_s"]
            # Exclude the boundary second to avoid a release transition.
            points = [p for p in path["points"] if p["time_s"] <= quiet_end - 1][-4:]
            if len(points) < 2:
                rows.append(
                    {
                        "right_proposal_id": item["right_proposal_id"],
                        "status": "no_preboundary_held_pair",
                        "pair_count": 0,
                        "pairs": [],
                    }
                )
                continue
            if any(panel_for_pixel(p["center_1080p_px"]) != 1 for p in points):
                raise ValueError("Held body path outside right panel")
            cache = {}

            def frame_at(time_s):
                index = round((time_s - SOURCE_OFFSET_S) * fps)
                if index not in cache:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, index)
                    ok, frame = cap.read()
                    if not ok:
                        raise ValueError(f"Latvia frame {index} unreadable")
                    cache[index] = resize_panel(frame, 1)
                return cache[index]

            pairs = []
            for first, second in zip(points, points[1:]):
                p0 = panel_pixel(first["center_1080p_px"], 1)
                p1 = panel_pixel(second["center_1080p_px"], 1)
                result = camera_relative_pair(p0, p1, first["time_s"], second["time_s"], frame_at)
                pairs.append(
                    {
                        "interval_s": [first["time_s"], second["time_s"]],
                        "raw_displacement_analysis_px": round(math.dist(p0, p1), 3),
                        **result,
                    }
                )
            row = {
                "right_proposal_id": item["right_proposal_id"],
                "highres_path_id": key[1],
                "colour": key[0],
                "quiet_end_time_s": quiet_end,
                "status": "audited",
                "pair_count": len(pairs),
                "registered_pair_count": sum(p["camera_residual_px"] is not None for p in pairs),
                "pairs": pairs,
            }
            rows.append(row)
            print(
                row["right_proposal_id"],
                row["registered_pair_count"],
                "/",
                row["pair_count"],
                flush=True,
            )
    finally:
        cap.release()
    payload = {
        "status": "czech_rule_latvia_preboundary_quiet_body_path_transfer_not_stationary_truth",
        "source_video_sha256": source_hash,
        "source_offset_s": SOURCE_OFFSET_S,
        "join_sha256": digest(JOIN),
        "yellow_path_sha256": digest(YELLOW),
        "red_path_sha256": digest(RED),
        "prior_moving_transfer_sha256": digest(FROZEN),
        "registration_code_sha256": code_hash,
        "runner_sha256": digest(Path(__file__)),
        "selection": "Unique high-resolution body path for each of 16 reviewed moving-stone pixel proposals; last four available 1 Hz points strictly before observed quiet-end boundary; no per-source retuning.",
        "reviewed_proposal_count": len(rows),
        "usable_path_count": sum(r["status"] == "audited" for r in rows),
        "pair_count": sum(r["pair_count"] for r in rows),
        "registered_pair_count": sum(r.get("registered_pair_count", 0) for r in rows),
        "status_counts": dict(Counter(r["status"] for r in rows)),
        "rows": rows,
        "limitations": [
            "Held/quiet classification comes from same-match source review and path selection; physical stationarity is not independently labelled.",
            "High-resolution body track may follow a person or change identity before the observed moving prefix.",
            "A low camera-relative residual does not establish physical release time or throw identity.",
        ],
    }
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n")
    print(
        json.dumps(
            {
                "usable": payload["usable_path_count"],
                "pairs": payload["pair_count"],
                "registered": payload["registered_pair_count"],
            }
        )
    )


if __name__ == "__main__":
    main()
