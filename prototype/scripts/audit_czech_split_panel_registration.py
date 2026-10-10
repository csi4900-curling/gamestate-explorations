"""Probe 2024 reviewed motion paths using panel-local camera registration."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from split_panel_camera_registration import (  # noqa: E402
    camera_relative_pair, panel_for_pixel, panel_pixel, resize_panel)

BASE = ROOT / "validation/throw-event-benchmark/canada-czech-2024"
SOURCE = BASE / "source-1080p-full-format270.mp4"
LEDGER = BASE / "full-reviewed-stone-replay-gaps-development.json"
HANDOFF = BASE / "full-reviewed-stone-continuation-handoff-development.json"
ALIGNMENT = BASE / "full-match-highres-alignment-postscore.json"
OUTPUT = BASE / "split-panel-registration-reviewed-paths-development.json"


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def audit_row(row, capture, fps):
    points = row["observed_left_motion_path"]
    if len(points) < 2:
        return {"episode_id": row["episode_id"], "status": "no_reviewed_path",
                "pair_count": 0, "pairs": []}
    panels = {panel_for_pixel(p["pixel_center_1080"]) for p in points}
    if len(panels) != 1:
        return {"episode_id": row["episode_id"],
                "status": "path_crosses_panel_boundary", "pair_count": 0,
                "pairs": []}
    panel = panels.pop()
    cache = {}

    def frame_at(time_s):
        index = round(time_s * fps)
        if index not in cache:
            capture.set(cv2.CAP_PROP_POS_FRAMES, index)
            ok, frame = capture.read()
            if not ok:
                raise ValueError(f"Frame {index} unreadable")
            cache[index] = resize_panel(frame, panel)
        return cache[index]

    pairs = []
    for first, second in zip(points, points[1:]):
        t0, t1 = first["source_time_s"], second["source_time_s"]
        p0 = panel_pixel(first["pixel_center_1080"], panel)
        p1 = panel_pixel(second["pixel_center_1080"], panel)
        result = camera_relative_pair(p0, p1, t0, t1, frame_at)
        pairs.append({"interval_s": [t0, t1],
                      "raw_displacement_px": round(float(np.linalg.norm(
                          np.asarray(p1) - np.asarray(p0))), 3),
                      **result})
    return {"episode_id": row["episode_id"], "status": "audited",
            "panel": "left" if panel == 0 else "right",
            "source_interval_s": [points[0]["source_time_s"],
                                  points[-1]["source_time_s"]],
            "point_count": len(points), "pair_count": len(pairs),
            "registered_pair_count": sum(p["camera_residual_px"] is not None
                                         for p in pairs),
            "pairs": pairs}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--episode", action="append",
                        help="Probe selected episode(s); default is all 21")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    ledger = json.loads(LEDGER.read_text())
    handoff = json.loads(HANDOFF.read_text())
    alignment = json.loads(ALIGNMENT.read_text())
    source_hash = digest(SOURCE)
    if (source_hash != handoff["source_video_sha256"] or
            handoff["input_sha256"]["replay_gaps"] != digest(LEDGER) or
            alignment["full_video_sha256"] != ledger["source_video_sha256"] or
            alignment["interval_video_sha256"] != source_hash or
            not alignment["all_best_at_zero_adjustment"] or
            alignment["source_offset_s"] != 0):
        raise ValueError("Reviewed path and full-resolution video lineage differs")
    selected = set(args.episode or [r["episode_id"] for r in ledger["rows"]])
    rows = [r for r in ledger["rows"] if r["episode_id"] in selected]
    if len(rows) != len(selected):
        raise ValueError("Unknown or duplicate requested episode")
    if args.output.exists():
        raise ValueError("Output already exists; preserve previous audit")
    capture = cv2.VideoCapture(str(SOURCE), cv2.CAP_FFMPEG,
                               [cv2.CAP_PROP_N_THREADS, 1])
    if not capture.isOpened():
        raise ValueError("Source unreadable")
    fps = capture.get(cv2.CAP_PROP_FPS)
    try:
        results = []
        for row in rows:
            result = audit_row(row, capture, fps)
            results.append(result)
            print(row["episode_id"], result["status"],
                  result.get("registered_pair_count", 0),
                  "/", result["pair_count"], flush=True)
    finally:
        capture.release()
    payload = {
        "status": "exploratory_panel_local_registration_not_throw_truth",
        "source_sha256": source_hash,
        "source_360p_sha256": ledger["source_video_sha256"],
        "reviewed_ledger_sha256": digest(LEDGER),
        "full_resolution_handoff_sha256": digest(HANDOFF),
        "cross_resolution_alignment_sha256": digest(ALIGNMENT),
        "registration_code_sha256": digest(ROOT /
            "prototype/split_panel_camera_registration.py"),
        "runner_sha256": digest(Path(__file__)),
        "panel_geometry": {"source_frame": [1920, 1080],
                           "source_panel": [960, 1080],
                           "analysis_panel": [640, 720],
                           "source_to_analysis_scale": 2 / 3},
        "method": "Panel-preserving aspect ratio; 0.25 s ice-region short-pair transforms; every subpair must register; 2022 reliability parameters adapted to panel shape without label fitting.",
        "selected_episode_ids": sorted(selected),
        "path_count": sum(r["status"] == "audited" for r in results),
        "pair_count": sum(r["pair_count"] for r in results),
        "registered_pair_count": sum(r.get("registered_pair_count", 0)
                                     for r in results),
        "panel_counts": dict(Counter(r.get("panel", "none") for r in results)),
        "rows": results,
        "limitations": [
            "Reviewed paths are development evidence, not independent physical throw labels.",
            "The broad ice-like mask is a source-image heuristic, not rink geometry.",
            "Camera residuals do not establish stone identity, throw precision or recall, or simulation-ready positions.",
        ],
    }
    args.output.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps({"paths": payload["path_count"],
                      "pairs": payload["pair_count"],
                      "registered_pairs": payload["registered_pair_count"],
                      "panels": payload["panel_counts"]}))


if __name__ == "__main__":
    main()
