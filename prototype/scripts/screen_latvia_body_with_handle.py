"""Require a coloured handle above each Latvia 1080p body-template proposal.

This is a development screen on a frozen proposal ledger, not event scoring.
"""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype/scripts"))
from probe_latvia_1080p_body_paths import link_paths

BASE = ROOT / "validation/throw-event-benchmark"
VIDEO_POSITIVE = BASE / "canada-latvia-2024/source-1080p-1650-2760.mp4"
VIDEO_BLIND = BASE / "canada-latvia-2024/source-1080p-5670-6670.mp4"
PROBE = (
    BASE
    / "layout-router/full-2024-coverage/latvia24-full-v1/end6-highres-body-template-development.json"
)
OUT = (
    BASE
    / "layout-router/full-2024-coverage/latvia24-full-v1/end6-highres-body-handle-screen-development.json"
)
HANDLE_MIN_PIXELS = 120
RELATIVE_BOX_XYXY = (-42, -55, 42, -8)


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
        raise RuntimeError(f"Could not decode at {seconds} s")
    return frame


def handle_evidence(frame, point):
    x, y = point["center_1080p_px"]
    dx1, dy1, dx2, dy2 = RELATIVE_BOX_XYXY
    crop = frame[y + dy1 : y + dy2, x + dx1 : x + dx2]
    if crop.shape[:2] != (dy2 - dy1, dx2 - dx1):
        raise ValueError("Handle observation outside source frame")
    hue, saturation, value = cv2.split(cv2.cvtColor(crop, cv2.COLOR_BGR2HSV))
    red = ((hue < 12) | (hue > 170)) & (saturation > 70) & (value > 45)
    yellow = (hue > 16) & (hue < 43) & (saturation > 70) & (value > 65)
    count = {"red": int(red.sum()), "yellow": int(yellow.sum())}
    return {
        "handle_colour_pixels": count,
        "handle_colour_claim": max(count, key=count.get),
        "handle_supported": bool(max(count.values()) >= HANDLE_MIN_PIXELS),
    }


def attach(rows, capture, clip_start_s):
    screened = []
    for row in rows:
        if not row["body_proposals"]:
            screened.append({"time_s": row["time_s"], "body_proposals": []})
            continue
        frame = frame_at(capture, row["time_s"] - clip_start_s)
        points = [{**point, **handle_evidence(frame, point)} for point in row["body_proposals"]]
        screened.append({"time_s": row["time_s"], "body_proposals": points})
    return screened


def main():
    if OUT.exists():
        raise SystemExit("Output exists; preserve first screen")
    prior = json.loads(PROBE.read_text())
    if prior["positive_video_sha256"] != digest(VIDEO_POSITIVE) or prior[
        "blind_video_sha256"
    ] != digest(VIDEO_BLIND):
        raise ValueError("Video source differs from body probe")
    positive_cap = cv2.VideoCapture(
        str(VIDEO_POSITIVE), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1]
    )
    blind_cap = cv2.VideoCapture(str(VIDEO_BLIND), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not positive_cap.isOpened() or not blind_cap.isOpened():
        raise RuntimeError("Cannot open source videos")
    try:
        positive = attach(prior["positive_control"], positive_cap, 1650)
        blind = attach(prior["samples"], blind_cap, 5670)
    finally:
        positive_cap.release()
        blind_cap.release()
    supported_samples = [
        {
            "time_s": row["time_s"],
            "body_proposals": [p for p in row["body_proposals"] if p["handle_supported"]],
        }
        for row in blind
    ]
    paths = link_paths(supported_samples)
    result = {
        "status": "body_plus_colour_handle_development_screen_not_throw_truth",
        "body_probe_sha256": digest(PROBE),
        "positive_video_sha256": digest(VIDEO_POSITIVE),
        "blind_video_sha256": digest(VIDEO_BLIND),
        "runner_sha256": digest(Path(__file__)),
        "linker_code_sha256": digest(ROOT / "prototype/scripts/probe_latvia_1080p_body_paths.py"),
        "relative_handle_box_xyxy_1080p": RELATIVE_BOX_XYXY,
        "handle_min_colour_pixels": HANDLE_MIN_PIXELS,
        "positive_control": positive,
        "blind_samples_with_body_proposals": [r for r in blind if r["body_proposals"]],
        "positive_supported_count": sum(
            p["handle_supported"] for r in positive for p in r["body_proposals"]
        ),
        "blind_body_proposal_count": sum(len(r["body_proposals"]) for r in blind),
        "blind_handle_supported_count": sum(
            p["handle_supported"] for r in blind for p in r["body_proposals"]
        ),
        "supported_path_direction_counts": dict(Counter(p["direction"] for p in paths)),
        "supported_image_paths": paths,
        "limitations": [
            "Threshold and box were chosen after reviewing one positive and the B006 wheelchair false path.",
            "A red or yellow garment over a grey shape can pass; a hidden handle can fail.",
            "Nearest-neighbour paths remain provisional image paths, not persistent stone identities.",
            "Independent full-interval labels are needed for throw precision and recall.",
        ],
    }
    OUT.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                "positive_supported": result["positive_supported_count"],
                "blind_body_proposals": result["blind_body_proposal_count"],
                "blind_handle_supported": result["blind_handle_supported_count"],
                "path_directions": result["supported_path_direction_counts"],
            }
        )
    )


if __name__ == "__main__":
    main()
