"""Frozen Latvia body-template transfer to separate Canada–Korea T11 clip.

This is a development transfer diagnostic, not an independent throw F1 test.
"""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype/scripts"))
from probe_latvia_1080p_body_paths import body_template, frame_at, link_paths, matches
from screen_latvia_body_with_handle import handle_evidence

LATVIA = ROOT / "validation/throw-event-benchmark/canada-latvia-2024/source-1080p-1650-2760.mp4"
VIDEO = ROOT / "prototype/continuous/clip.mp4"
TRACK = ROOT / "prototype/cross-view/results.json"
RED_AUDIT = (
    ROOT
    / "validation/throw-event-benchmark/layout-router/full-2024-coverage/latvia24-full-v1/early-highres-red-template-selected-development.json"
)
OUT = (
    ROOT
    / "validation/throw-event-benchmark/canada-korea-2024/latvia-body-template-transfer-v2-development.json"
)
SOURCE_START_S, SOURCE_STOP_S = 2260, 2350
SEARCH_XYXY = (990, 520, 1890, 970)


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def local_score(frame, template, cap_pixel):
    x1, y1, x2, y2 = SEARCH_XYXY
    gray = cv2.resize(
        cv2.cvtColor(frame[y1:y2, x1:x2], cv2.COLOR_BGR2GRAY),
        ((x2 - x1) // 2, (y2 - y1) // 2),
        interpolation=cv2.INTER_AREA,
    )
    corr = cv2.matchTemplate(gray, template, cv2.TM_CCOEFF_NORMED)
    # The T11 track is centred near the cap, so +15 px is an explicit
    # postreview diagnostic search centre, not a frozen detector input.
    tx, ty = cap_pixel
    px = round((tx - x1 - 40) / 2)
    py = round((ty + 15 - y1 - 19) / 2)
    body_center_inside_search = 0 <= px < corr.shape[1] and 0 <= py < corr.shape[0]
    left, right = max(0, px - 25), min(corr.shape[1], px + 26)
    top, bottom = max(0, py - 25), min(corr.shape[0], py + 26)
    patch = corr[top:bottom, left:right]
    return {
        "tracked_cap_pixel_1080p": cap_pixel,
        "diagnostic_body_y_offset_px": 15,
        "assumed_body_center_in_search": bool(body_center_inside_search),
        "local_score_within_50px": round(float(patch.max()), 5)
        if body_center_inside_search and patch.size
        else None,
        "global_max_score": round(float(corr.max()), 5),
    }


def main():
    if OUT.exists():
        raise SystemExit("Output exists; preserve first cross-match transfer")
    red_audit = json.loads(RED_AUDIT.read_text())
    if red_audit["video_sha256"] != digest(LATVIA):
        raise ValueError("Latvia template source changed")
    track_data = json.loads(TRACK.read_text())
    t11 = next(row for row in track_data["throws"] if row["id"] == "T11")
    if t11["colour"] != "yellow":
        raise ValueError("T11 track colour changed")
    src = cv2.VideoCapture(str(LATVIA), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    target = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if (
        not src.isOpened()
        or not target.isOpened()
        or src.get(cv2.CAP_PROP_FPS) != 30
        or target.get(cv2.CAP_PROP_FPS) != 30
    ):
        raise RuntimeError("Could not open both expected 30-fps clips")
    try:
        yellow_template = body_template(frame_at(src, 2310 - 1650))
        x1, y1, x2, y2 = red_audit["template_xyxy_1080p"]
        red_frame = frame_at(src, red_audit["template_source_time_s"] - 1650)
        red_template = cv2.resize(
            cv2.cvtColor(red_frame[y1:y2, x1:x2], cv2.COLOR_BGR2GRAY),
            (40, 19),
            interpolation=cv2.INTER_AREA,
        )
        samples = []
        target.set(cv2.CAP_PROP_POS_FRAMES, 0)
        for t in range(SOURCE_START_S, SOURCE_STOP_S):
            ok, frame = target.read()
            if not ok or frame.shape[:2] != (1080, 1920):
                raise RuntimeError(f"Could not decode {t}")
            by_colour = {}
            for colour, template in (("yellow", yellow_template), ("red", red_template)):
                points = [{**p, **handle_evidence(frame, p)} for p in matches(frame, template)]
                for point in points:
                    point["matching_colour_handle_supported"] = bool(
                        point["handle_colour_pixels"][colour] >= 120
                    )
                by_colour[colour] = points
            samples.append({"time_s": t, "proposals": by_colour})
            if t + 1 < SOURCE_STOP_S:
                for _ in range(29):
                    if not target.grab():
                        raise RuntimeError(f"Could not advance from {t}")
        track_audit = []
        for point in t11["arrival"]:
            t = point["time_s"]
            if not 2312.5 <= t <= 2316.5:
                continue
            frame = frame_at(target, t - SOURCE_START_S)
            track_audit.append({"time_s": t, **local_score(frame, yellow_template, point["pixel"])})
    finally:
        src.release()
        target.release()
    paths = {}
    for colour in ("yellow", "red"):
        screened = [
            {
                "time_s": r["time_s"],
                "body_proposals": [
                    p for p in r["proposals"][colour] if p["matching_colour_handle_supported"]
                ],
            }
            for r in samples
        ]
        paths[colour] = link_paths(screened)
    result = {
        "status": "cross_match_partial_lower_ice_t11_path_not_full_receiving_track",
        "source_match": "Canada–Korea 2024",
        "target_video_sha256": digest(VIDEO),
        "latvia_template_video_sha256": digest(LATVIA),
        "red_template_audit_sha256": digest(RED_AUDIT),
        "t11_track_sha256": digest(TRACK),
        "runner_sha256": digest(Path(__file__)),
        "body_code_sha256": digest(ROOT / "prototype/scripts/probe_latvia_1080p_body_paths.py"),
        "handle_code_sha256": digest(ROOT / "prototype/scripts/screen_latvia_body_with_handle.py"),
        "source_interval_s": [SOURCE_START_S, SOURCE_STOP_S],
        "sample_period_s": 1,
        "frozen_search_xyxy_1080p": SEARCH_XYXY,
        "body_score_floor": 0.55,
        "matching_colour_handle_min_pixels": 120,
        "proposal_counts": {
            colour: {
                "body": sum(len(r["proposals"][colour]) for r in samples),
                "handle_supported": sum(
                    p["matching_colour_handle_supported"]
                    for r in samples
                    for p in r["proposals"][colour]
                ),
            }
            for colour in ("yellow", "red")
        },
        "supported_path_direction_counts": {
            colour: dict(Counter(p["direction"] for p in paths[colour])) for colour in paths
        },
        "image_motion_paths": paths,
        "t11_diagnostic_track_local_scores": track_audit,
        "samples_with_proposals": [r for r in samples if any(r["proposals"].values())],
        "limitations": [
            "The target T11 image track is provisional and was used only to diagnose visibility; it is not an independent label.",
            "The +15 px body-centre offset is postreview diagnostic geometry, not part of the frozen detector.",
            "T11 leaves the Latvia search region as it approaches the house.",
            "This one clip cannot measure cross-recording event F1.",
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                "counts": result["proposal_counts"],
                "paths": result["supported_path_direction_counts"],
                "t11_local_scores": [r["local_score_within_50px"] for r in track_audit],
            }
        )
    )


if __name__ == "__main__":
    main()
