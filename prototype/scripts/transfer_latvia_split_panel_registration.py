"""Transfer the Czech-developed panel registration to Latvia end-six paths."""

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

CZECH = ROOT / "validation/throw-event-benchmark/canada-czech-2024"
BASE = ROOT / "validation/throw-event-benchmark/canada-latvia-2024"
VIDEO = BASE / "source-1080p-5670-6670.mp4"
JOIN = BASE / "end6-cross-resolution-body-cap-development.json"
FROZEN_POSITIVE = CZECH / "split-panel-registration-reviewed-paths-edge-guard-v2-development.json"
FROZEN_CONTROL = CZECH / "split-panel-registration-board-controls-edge-guard-v2-development.json"
OUTPUT = BASE / "end6-split-panel-registration-czech-rule-transfer-development.json"
SOURCE_OFFSET_S = 5670


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def main():
    if OUTPUT.exists():
        raise ValueError("Latvia transfer already exists")
    join = json.loads(JOIN.read_text())
    frozen_positive = json.loads(FROZEN_POSITIVE.read_text())
    frozen_control = json.loads(FROZEN_CONTROL.read_text())
    code_hash = digest(ROOT / "prototype/split_panel_camera_registration.py")
    source_hash = digest(VIDEO)
    if (
        source_hash != join["highres_source_sha256"]
        or join["source_interval_s"] != [5670, 6670]
        or code_hash != frozen_positive["registration_code_sha256"]
        or code_hash != frozen_control["registration_code_sha256"]
        or len(join["rows"]) != 20
    ):
        raise ValueError("Latvia source or Czech-frozen rule lineage differs")
    capture = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not capture.isOpened():
        raise ValueError("Latvia source unreadable")
    fps = capture.get(cv2.CAP_PROP_FPS)
    rows = []
    try:
        for item in join["rows"]:
            original = item["observed_motion_onset"].get("observed_moving_points", [])
            points = [
                {"time_s": p["time_s"], "full_pixel": [3 * value for value in p["pixel"]]}
                for p in original
            ]
            if len(points) < 2:
                rows.append(
                    {
                        "right_proposal_id": item["right_proposal_id"],
                        "source_prefix_class": item["source_prefix_class"],
                        "status": "no_usable_reviewed_motion_path",
                        "pair_count": 0,
                        "pairs": [],
                    }
                )
                continue
            panels = {panel_for_pixel(p["full_pixel"]) for p in points}
            if panels != {1}:
                raise ValueError("Latvia right-view path leaves expected panel")
            cache = {}

            def frame_at(time_s):
                index = round((time_s - SOURCE_OFFSET_S) * fps)
                if index not in cache:
                    capture.set(cv2.CAP_PROP_POS_FRAMES, index)
                    ok, frame = capture.read()
                    if not ok:
                        raise ValueError(f"Latvia frame {index} unreadable")
                    cache[index] = resize_panel(frame, 1)
                return cache[index]

            pairs = []
            for first, second in zip(points, points[1:]):
                p0 = panel_pixel(first["full_pixel"], 1)
                p1 = panel_pixel(second["full_pixel"], 1)
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
                "source_prefix_class": item["source_prefix_class"],
                "status": "audited",
                "source_interval_s": [points[0]["time_s"], points[-1]["time_s"]],
                "point_count": len(points),
                "pair_count": len(pairs),
                "registered_pair_count": sum(p["camera_residual_px"] is not None for p in pairs),
                "pairs": pairs,
            }
            rows.append(row)
            print(
                row["right_proposal_id"],
                row["source_prefix_class"],
                row["registered_pair_count"],
                "/",
                row["pair_count"],
                flush=True,
            )
    finally:
        capture.release()
    payload = {
        "status": "czech_developed_camera_registration_latvia_cross_recording_development_transfer",
        "source_video_sha256": source_hash,
        "source_offset_s": SOURCE_OFFSET_S,
        "join_sha256": digest(JOIN),
        "frozen_czech_positive_sha256": digest(FROZEN_POSITIVE),
        "frozen_czech_control_sha256": digest(FROZEN_CONTROL),
        "registration_code_sha256": code_hash,
        "runner_sha256": digest(Path(__file__)),
        "method": "Unchanged Czech panel-local 0.25 s ice-region registration with scene-edge abstention; reviewed 360p pixel centers multiplied by 3 then placed in right 960x1080 source panel and aspect-preserving 640x720 analysis frame.",
        "reviewed_proposal_count": len(rows),
        "usable_path_count": sum(r["status"] == "audited" for r in rows),
        "pair_count": sum(r["pair_count"] for r in rows),
        "registered_pair_count": sum(r.get("registered_pair_count", 0) for r in rows),
        "source_class_counts": dict(Counter(r["source_prefix_class"] for r in rows)),
        "rows": rows,
        "limitations": [
            "Latvia and Czechia use a similar 2024 broadcast style and both recordings were previously exposed to development.",
            "Source-reviewed pixel class is same-agent path review, not independent physical throw truth.",
            "An accepted camera-relative motion cue does not distinguish stone from person, identify release or settle, or verify a simulation-ready game state.",
        ],
    }
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n")
    print(
        json.dumps(
            {
                "usable_paths": payload["usable_path_count"],
                "pairs": payload["pair_count"],
                "registered": payload["registered_pair_count"],
                "classes": payload["source_class_counts"],
            }
        )
    )


if __name__ == "__main__":
    main()
