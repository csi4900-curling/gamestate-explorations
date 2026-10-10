"""Compare upsampled 360p split registration with frozen 1080p probes."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from lowres_split_panel_camera_registration import source_pair  # noqa: E402

BASE = ROOT / "validation/throw-event-benchmark/canada-czech-2024"
VIDEO = BASE / "source-360p.mp4"
ALIGNMENT = BASE / "full-match-highres-alignment-postscore.json"
PATHS = BASE / "full-reviewed-stone-replay-gaps-development.json"
CONTROL = BASE / "split-panel-registration-board-controls-edge-guard-v2-development.json"
PRIOR = BASE / "split-panel-registration-reviewed-paths-edge-guard-v2-development.json"
OUT = BASE / "lowres-split-registration-positive-and-board-controls-development.json"


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def main():
    if OUT.exists():
        raise ValueError("Low-resolution registration audit already exists")
    alignment, paths, control, prior = (
        json.loads(p.read_text()) for p in (ALIGNMENT, PATHS, CONTROL, PRIOR)
    )
    source_hash = digest(VIDEO)
    high_hash = prior["source_sha256"]
    if (
        source_hash != paths["source_video_sha256"]
        or source_hash != alignment["full_video_sha256"]
        or high_hash != alignment["interval_video_sha256"]
        or high_hash != control["source_sha256"]
        or not alignment["all_best_at_zero_adjustment"]
        or prior["reviewed_ledger_sha256"] != digest(PATHS)
        or prior["registration_code_sha256"]
        != digest(ROOT / "prototype/split_panel_camera_registration.py")
        or control["registration_code_sha256"]
        != digest(ROOT / "prototype/split_panel_camera_registration.py")
    ):
        raise ValueError("Czech source or high-resolution reference differs")
    cap = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        raise ValueError("Czech 360p video unreadable")
    fps = cap.get(cv2.CAP_PROP_FPS)

    def frame_at(time_s):
        index = round(time_s * fps)
        cap.set(cv2.CAP_PROP_POS_FRAMES, index)
        ok, frame = cap.read()
        if not ok:
            raise ValueError(f"Frame {index} unreadable")
        return frame

    high_path_by_id = {r["episode_id"]: r for r in prior["rows"]}
    results = []
    try:
        for row in paths["rows"]:
            points = row["observed_left_motion_path"]
            if len(points) < 2:
                continue
            old = high_path_by_id[row["episode_id"]]["pairs"]
            if len(old) != len(points) - 1:
                raise ValueError("High-resolution path pair count changed")
            for index, (first, second) in enumerate(zip(points, points[1:])):
                t0, t1 = first["source_time_s"], second["source_time_s"]
                if old[index]["interval_s"] != [t0, t1]:
                    raise ValueError("High-resolution pair order changed")
                result = source_pair(
                    [v / 3 for v in first["pixel_center_1080"]],
                    [v / 3 for v in second["pixel_center_1080"]],
                    t0,
                    t1,
                    frame_at,
                )
                results.append(
                    {
                        "group": "reviewed_moving_path",
                        "id": row["episode_id"],
                        "interval_s": [t0, t1],
                        "highres_residual_px": old[index]["camera_residual_px"],
                        "lowres": result,
                    }
                )
            print(row["episode_id"], "moving", len(points) - 1, flush=True)
        for row in control["rows"]:
            t0, t1 = row["interval_s"]
            result = source_pair(
                [v / 3 for v in row["first_pixel_1080"]],
                [v / 3 for v in row["second_pixel_1080"]],
                t0,
                t1,
                frame_at,
            )
            results.append(
                {
                    "group": row["control_group"],
                    "id": row["candidate_id"],
                    "interval_s": [t0, t1],
                    "highres_residual_px": row["camera_residual_px"],
                    "lowres": result,
                }
            )
        print("board_controls", len(control["rows"]), flush=True)
    finally:
        cap.release()
    groups = sorted({r["group"] for r in results})
    summary = {}
    for group in groups:
        subset = [r for r in results if r["group"] == group]
        accepted = [r for r in subset if r["lowres"]["camera_residual_px"] is not None]
        summary[group] = {
            "pair_count": len(subset),
            "registered_count": len(accepted),
            "residual_over_5_count": sum(r["lowres"]["camera_residual_px"] > 5 for r in accepted),
            "highres_registered_count": sum(r["highres_residual_px"] is not None for r in subset),
            "lowres_abstention_statuses": dict(
                Counter(
                    r["lowres"]["subpairs"][-1]["status"]
                    if r["lowres"]["subpairs"]
                    else r["lowres"]["status"]
                    for r in subset
                    if r["lowres"]["camera_residual_px"] is None
                )
            ),
        }
    payload = {
        "status": "upsampled_360p_split_registration_development_comparison_not_throw_truth",
        "source_video_sha256": source_hash,
        "source_1080p_sha256": high_hash,
        "input_sha256": {
            "alignment": digest(ALIGNMENT),
            "reviewed_paths": digest(PATHS),
            "highres_controls": digest(CONTROL),
            "highres_moving_paths": digest(PRIOR),
        },
        "lowres_adapter_sha256": digest(
            ROOT / "prototype/lowres_split_panel_camera_registration.py"
        ),
        "registration_code_sha256": digest(ROOT / "prototype/split_panel_camera_registration.py"),
        "runner_sha256": digest(Path(__file__)),
        "method": "Use verified zero-offset 360p↔1080p alignment; scale reviewed 1080p pixels by 1/3, crop their 320x360 source panel, upsample 2x without distortion, apply unchanged 640x720 camera registration and edge guard.",
        "summary_by_group": summary,
        "rows": results,
        "limitations": [
            "Upsampling does not restore high-resolution detail; the frozen high-resolution rule was not originally calibrated for 360p imagery.",
            "Reviewed moving paths and quiet-board controls are selected development observations, not independent physical throw labels.",
            "Some board controls are localization jitter or identity ambiguity rather than proven stationary stones.",
            "A 5 px motion residual alone is not a physical throw decision.",
        ],
    }
    OUT.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
