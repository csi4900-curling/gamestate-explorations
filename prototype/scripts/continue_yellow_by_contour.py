"""Continue an observed yellow-stone body path with raw handle contours.

Development-only: geometry and motion association are fitted on exposed Korea
and Slovakia examples. Contours can follow another object near occlusion.
"""

import argparse
from hashlib import sha256
import json
from math import hypot
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from red_motion_window import split_moving_prefix
from scripts.transfer_yellow_template_cap_handoff import TARGETS

OUT_NAMES = {
    "korea-regression": "validation/throw-event-benchmark/canada-korea-2024/yellow-contour-continuation-development.json",
    "slovakia-transfer": "validation/throw-event-benchmark/canada-slovakia-2024/yellow-contour-continuation-development.json",
}
BODY_PROXY_OFFSET_1080P_PX = 18
ICE_ROI_1080P = (990, 400, 1890, 970)
MAX_LINK_SPEED_1080P_PX_PER_S = 130
MAX_GAP_S = 2
MAX_EXTENSION_S = 20
STABLE_STEP_1080P_PX = 4
STABLE_STEPS = 3


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def yellow_contours(frame):
    image = cv2.resize(frame, (640, 360), interpolation=cv2.INTER_AREA)
    hue, saturation, value = cv2.split(cv2.cvtColor(image, cv2.COLOR_BGR2HSV))
    mask = (hue > 16) & (hue < 43) & (saturation > 60) & (value > 65)
    contours, _ = cv2.findContours(
        mask.astype("uint8") * 255, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    points = []
    x1, y1, x2, y2 = ICE_ROI_1080P
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        area = cv2.contourArea(contour)
        if area < 15 or w > 160 or h > 100:
            continue
        center = [3 * (x + w / 2), 3 * (y + h / 2) + BODY_PROXY_OFFSET_1080P_PX]
        if not (x1 <= center[0] <= x2 and y1 <= center[1] <= y2):
            continue
        points.append(
            {
                "center_1080p_px": center,
                "handle_bbox_360p": [x, y, w, h],
                "handle_area_360p_px2": round(float(area), 2),
            }
        )
    return points


def continue_path(seed, frames):
    points = [
        {
            "time_s": p["time_s"],
            "center_1080p_px": p["center_1080p_px"],
            "cue": "body_template_plus_yellow_handle",
        }
        for p in seed["points"]
    ]
    seed_last = points[-1]["time_s"]
    decisions = []
    for row in frames:
        t = row["source_time_s"]
        if t <= seed_last:
            continue
        if t - seed_last > MAX_EXTENSION_S:
            break
        gap = t - points[-1]["time_s"]
        if gap > MAX_GAP_S:
            break
        latest = points[-1]["center_1080p_px"]
        before = points[-2]["center_1080p_px"]
        previous_gap = points[-1]["time_s"] - points[-2]["time_s"]
        velocity = [(latest[a] - before[a]) / previous_gap for a in (0, 1)]
        prediction = [latest[a] + velocity[a] * gap for a in (0, 1)]
        choices = []
        for p in row["raw_yellow_handle_contours"]:
            xy = p["center_1080p_px"]
            step = hypot(xy[0] - latest[0], xy[1] - latest[1])
            if step > MAX_LINK_SPEED_1080P_PX_PER_S * gap:
                continue
            prediction_error = hypot(xy[0] - prediction[0], xy[1] - prediction[1])
            choices.append((prediction_error + 0.25 * step, step, p))
        if not choices:
            decisions.append({"time_s": t, "status": "no_contour_in_motion_gate"})
            continue
        cost, step, chosen = min(choices)
        points.append(
            {
                "time_s": t,
                "center_1080p_px": chosen["center_1080p_px"],
                "cue": "raw_yellow_handle_contour_body_proxy",
                "handle_bbox_360p": chosen["handle_bbox_360p"],
            }
        )
        decisions.append(
            {
                "time_s": t,
                "status": "contour_linked",
                "eligible_count": len(choices),
                "step_1080p_px": round(step, 2),
                "prediction_cost_1080p_px": round(cost, 2),
            }
        )
        stop = split_moving_prefix(
            points, stable_step_px=STABLE_STEP_1080P_PX, stable_steps=STABLE_STEPS
        )
        if stop["visual_stop_bracket_s"] is not None:
            break
    return {
        "seed_path_id": seed["diagnostic_path_id"],
        "seed_interval_s": [seed["first_observed_s"], seed["last_observed_s"]],
        "points": points,
        "link_decisions": decisions,
        "image_motion_interpretation": split_moving_prefix(
            points, stable_step_px=STABLE_STEP_1080P_PX, stable_steps=STABLE_STEPS
        ),
        "same_stone_identity_verified": False,
        "physical_stop_verified": False,
        "simulation_ready": False,
    }


def run(target_name):
    cfg = TARGETS[target_name]
    out = ROOT / OUT_NAMES[target_name]
    if out.exists():
        raise SystemExit("Output exists; preserve first contour continuation")
    prior = json.loads(cfg["output"].read_text())
    if prior["target_video_sha256"] != digest(cfg["video"]):
        raise ValueError("Source differs from frozen body scan")
    seeds = [p for p in prior["body_image_paths"] if p["direction"] == "upward"]
    cap = cv2.VideoCapture(str(cfg["video"]), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened() or cap.get(cv2.CAP_PROP_FPS) != 30:
        raise RuntimeError("Cannot open expected 30-fps clip")
    rows = []
    try:
        start, stop = cfg["interval_s"]
        cap.set(cv2.CAP_PROP_POS_FRAMES, (start - cfg["offset_s"]) * 30)
        for t in range(start, stop):
            ok, frame = cap.read()
            if not ok or frame.shape[:2] != (1080, 1920):
                raise RuntimeError(f"Could not decode {t}")
            rows.append({"source_time_s": t, "raw_yellow_handle_contours": yellow_contours(frame)})
            if t + 1 < stop:
                for _ in range(29):
                    if not cap.grab():
                        raise RuntimeError(f"Could not advance from {t}")
    finally:
        cap.release()
    joined = [continue_path(p, rows) for p in seeds]
    result = {
        "status": "postreview_raw_colour_contour_continuation_development",
        "target_name": target_name,
        "target_video_sha256": digest(cfg["video"]),
        "frozen_body_scan_sha256": digest(cfg["output"]),
        "stop_rule_code_sha256": digest(ROOT / "prototype/red_motion_window.py"),
        "runner_sha256": digest(Path(__file__)),
        "source_interval_s": cfg["interval_s"],
        "sample_period_s": 1,
        "handle_hsv_hue_exclusive": [16, 43],
        "body_proxy_y_offset_1080p_px": BODY_PROXY_OFFSET_1080P_PX,
        "ice_roi_1080p": ICE_ROI_1080P,
        "max_link_speed_1080p_px_per_s": MAX_LINK_SPEED_1080P_PX_PER_S,
        "raw_contour_count": sum(len(r["raw_yellow_handle_contours"]) for r in rows),
        "seed_count": len(seeds),
        "joined_image_paths": joined,
        "rows_with_contours": [r for r in rows if r["raw_yellow_handle_contours"]],
        "limitations": [
            "The +18px cap-to-body proxy and predicted-centre cost were designed after Korea and Slovakia source review.",
            "Raw colour contours can attach to a different stone, player, broom or rink marking.",
            "The body proxy is an image centre, not a calibrated stone footprint or ground position.",
            "Visual stillness and apparent identity need independent validation; no game state is inferred.",
        ],
    }
    out.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                "target": target_name,
                "contours": result["raw_contour_count"],
                "paths": [
                    (
                        p["seed_interval_s"],
                        p["points"][-1]["time_s"],
                        p["image_motion_interpretation"]["visual_stop_bracket_s"],
                    )
                    for p in joined
                ],
            }
        )
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", choices=sorted(TARGETS), required=True)
    run(parser.parse_args().target)


if __name__ == "__main__":
    main()
