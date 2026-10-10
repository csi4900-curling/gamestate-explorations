"""Template-based 1080p stone-body proposal probe in Latvia's blind interval.

One source-visible moving stone supplies a frozen grey-body template. Matches
and nearest-neighbour paths are diagnostics, never automatic throw labels.
"""

from collections import Counter
from hashlib import sha256
import json
from math import hypot
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark/canada-latvia-2024"
POSITIVE = BASE / "source-1080p-1650-2760.mp4"
BLIND = BASE / "source-1080p-5670-6670.mp4"
OUT = ROOT / "validation/throw-event-benchmark/layout-router/full-2024-coverage/latvia24-full-v1/end6-highres-body-template-development.json"
POSITIVE_TIME_S = 2310
POSITIVE_CLIP_START_S = 1650
BLIND_START_S, BLIND_STOP_S = 5670, 6670
TEMPLATE_XYXY = (1268, 833, 1348, 870)  # grey body, below yellow handle
SEARCH_XYXY = (990, 520, 1890, 970)
SCORE_FLOOR = 0.55
MAX_PEAKS = 10
NMS_SIDE_HALFRES = 31


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def frame_at(capture, seconds):
    capture.set(cv2.CAP_PROP_POS_MSEC, seconds * 1000)
    ok, frame = capture.read()
    if not ok or frame.shape[:2] != (1080, 1920):
        raise RuntimeError(f"Unable to decode 1080p source at {seconds} s")
    return frame


def body_template(frame):
    x1, y1, x2, y2 = TEMPLATE_XYXY
    gray = cv2.cvtColor(frame[y1:y2, x1:x2], cv2.COLOR_BGR2GRAY)
    return cv2.resize(gray, (40, 19), interpolation=cv2.INTER_AREA)


def matches(frame, template):
    x1, y1, x2, y2 = SEARCH_XYXY
    gray = cv2.cvtColor(frame[y1:y2, x1:x2], cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, ((x2-x1)//2, (y2-y1)//2),
                      interpolation=cv2.INTER_AREA)
    corr = cv2.matchTemplate(gray, template, cv2.TM_CCOEFF_NORMED)
    peaks = []
    for _ in range(MAX_PEAKS):
        _, score, _, point = cv2.minMaxLoc(corr)
        if score < SCORE_FLOOR:
            break
        px, py = point
        peaks.append({"center_1080p_px": [x1 + 2*px + 40, y1 + 2*py + 19],
                      "score": round(float(score), 5)})
        cv2.rectangle(corr,
                      (max(0, px-NMS_SIDE_HALFRES), max(0, py-NMS_SIDE_HALFRES)),
                      (min(corr.shape[1]-1, px+NMS_SIDE_HALFRES),
                       min(corr.shape[0]-1, py+NMS_SIDE_HALFRES)),
                      -1, thickness=-1)
    return peaks


def link_paths(samples):
    paths = []
    for sample in samples:
        t = sample["time_s"]
        claimed = set()
        for path in sorted(paths, key=lambda p: p["points"][-1]["time_s"],
                           reverse=True):
            last = path["points"][-1]
            gap = t-last["time_s"]
            if gap <= 0 or gap > 2:
                continue
            choices = []
            for index, point in enumerate(sample["body_proposals"]):
                if index in claimed:
                    continue
                distance = hypot(*(point["center_1080p_px"][axis] -
                                   last["center_1080p_px"][axis]
                                   for axis in (0, 1)))
                if distance <= 130*gap:
                    choices.append((distance, index))
            if choices:
                _, index = min(choices)
                path["points"].append({"time_s": t,
                                       **sample["body_proposals"][index]})
                claimed.add(index)
        for index, point in enumerate(sample["body_proposals"]):
            if index not in claimed:
                paths.append({"points": [{"time_s": t, **point}]})
    supported = []
    for path in paths:
        points = path["points"]
        if len(points) < 3:
            continue
        span_y = points[-1]["center_1080p_px"][1] - points[0]["center_1080p_px"][1]
        if abs(span_y) < 75:
            continue
        path["direction"] = "upward" if span_y < 0 else "downward"
        path["vertical_span_1080p_px"] = span_y
        path["first_observed_s"] = points[0]["time_s"]
        path["last_observed_s"] = points[-1]["time_s"]
        supported.append(path)
    supported.sort(key=lambda p: p["first_observed_s"])
    for index, path in enumerate(supported, 1):
        path["diagnostic_path_id"] = f"B{index:03d}"
    return supported


def main():
    if OUT.exists():
        raise SystemExit("Output exists; preserve first diagnostic")
    positive = cv2.VideoCapture(str(POSITIVE), cv2.CAP_FFMPEG,
                                [cv2.CAP_PROP_N_THREADS, 1])
    blind = cv2.VideoCapture(str(BLIND), cv2.CAP_FFMPEG,
                             [cv2.CAP_PROP_N_THREADS, 1])
    if not positive.isOpened() or not blind.isOpened():
        raise RuntimeError("Cannot open both 1080p clips")
    try:
        template = body_template(frame_at(
            positive, POSITIVE_TIME_S-POSITIVE_CLIP_START_S))
        positive_control = [
            {"time_s": t, "body_proposals": matches(
                frame_at(positive, t-POSITIVE_CLIP_START_S), template)}
            for t in range(2309, 2316)]
        samples = [
            {"time_s": t, "body_proposals": matches(
                frame_at(blind, t-BLIND_START_S), template)}
            for t in range(BLIND_START_S, BLIND_STOP_S)]
    finally:
        positive.release()
        blind.release()
    paths = link_paths(samples)
    result = {
        "status": "single_example_body_template_development_not_stone_or_throw_truth",
        "positive_video_sha256": digest(POSITIVE),
        "blind_video_sha256": digest(BLIND),
        "runner_sha256": digest(Path(__file__)),
        "positive_source_time_s": POSITIVE_TIME_S,
        "positive_clip_start_s": POSITIVE_CLIP_START_S,
        "blind_source_interval_s": [BLIND_START_S, BLIND_STOP_S],
        "template_xyxy_1080p": TEMPLATE_XYXY,
        "search_xyxy_1080p": SEARCH_XYXY,
        "template_size_halfres_px": [40, 19],
        "match_method": "grayscale_CCOEFF_NORMED_half_resolution",
        "score_floor": SCORE_FLOOR,
        "max_peaks_per_second": MAX_PEAKS,
        "peak_suppression_side_halfres_px": NMS_SIDE_HALFRES,
        "path_link_max_speed_1080p_px_per_s": 130,
        "path_link_max_gap_s": 2,
        "supported_path_min_samples": 3,
        "supported_path_min_absolute_vertical_span_px": 75,
        "positive_control": positive_control,
        "samples": samples,
        "supported_path_direction_counts": dict(Counter(p["direction"] for p in paths)),
        "supported_image_paths": paths,
        "limitations": [
            "The source template is one prediction-selected visible yellow moving stone.",
            "Texture matching can respond to stationary stones, people or equipment.",
            "Greedy image paths can switch identities; motion direction alone is not delivery.",
            "No independent exhaustive labels, object recall or throw F1 are inferred.",
        ],
    }
    OUT.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"positive_control_peak_scores": [
        max((p["score"] for p in row["body_proposals"]), default=None)
        for row in positive_control],
        "blind_proposal_count": sum(len(row["body_proposals"]) for row in samples),
        "supported_path_direction_counts": result["supported_path_direction_counts"]}))


if __name__ == "__main__":
    main()
