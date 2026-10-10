"""Reproduce the selected Latvia-to-Scotland crossing darkness transfer check.

This is a failure-mode diagnostic, not a throw classifier or validation set.
"""

from hashlib import sha256
import json
from pathlib import Path

import cv2


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark"
ARTIFACT = BASE / "layout-router/full-2024-coverage"
PATCH_WIDTH = 32
PATCH_HEIGHT = 50
DARK_GRAY_BELOW = 140
LATVIA_EXPLORATORY_CUT = 0.2


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read(path):
    return json.loads(path.read_text())


def measure(video, cases):
    capture = cv2.VideoCapture(str(video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    fps = capture.get(cv2.CAP_PROP_FPS)
    if not capture.isOpened() or fps <= 0:
        raise RuntimeError(f"Unreadable video: {video}")
    rows = []
    for case in cases:
        capture.set(cv2.CAP_PROP_POS_FRAMES, round(case["time_s"] * fps))
        ok, frame = capture.read()
        if not ok:
            raise RuntimeError(f"Could not decode {case['id']} at {case['time_s']}")
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        x, y = (round(coordinate) for coordinate in case["point_px"])
        x0, x1 = max(0, x - PATCH_WIDTH // 2), min(gray.shape[1], x + PATCH_WIDTH // 2)
        y0, y1 = max(0, y), min(gray.shape[0], y + PATCH_HEIGHT)
        patch = gray[y0:y1, x0:x1]
        if patch.size == 0:
            raise ValueError(f"Empty patch at {case['id']}")
        rows.append(
            {
                **case,
                "patch_xyxy_px": [x0, y0, x1, y1],
                "dark_fraction": round(float((patch < DARK_GRAY_BELOW).mean()), 6),
                "latvia_exploratory_cut_says_nonstone": bool(
                    (patch < DARK_GRAY_BELOW).mean() >= LATVIA_EXPLORATORY_CUT
                ),
            }
        )
    capture.release()
    return rows, fps


def main():
    latvia_dir = ARTIFACT / "latvia24-full-v1"
    scotland_dir = ARTIFACT / "scotland24-bridged-development"
    sources = {
        "latvia": BASE / "canada-latvia-2024/source-360p.mp4",
        "scotland": BASE / "canada-scotland-2024/source-360p.mp4",
    }
    inputs = {
        "latvia_ledger": latvia_dir / "source-pixel-review-ledger.json",
        "latvia_accepted_probe": latvia_dir / "public-box-accepted-probe.json",
        "latvia_withheld_probe": latvia_dir / "public-box-withheld-probe.json",
        "scotland_classes": scotland_dir / "bridge-crossing-source-classes-development.json",
        "scotland_probe": scotland_dir / "public-box-crossing-probe.json",
    }
    data = {key: read(path) for key, path in inputs.items()}
    source_hashes = {key: digest(path) for key, path in sources.items()}
    if data["latvia_ledger"]["source_sha256"] != source_hashes["latvia"]:
        raise ValueError("Latvia ledger source hash mismatch")
    if data["scotland_classes"]["source_sha256"] != source_hashes["scotland"]:
        raise ValueError("Scotland review source hash mismatch")
    for key in ("latvia_accepted_probe", "latvia_withheld_probe"):
        if data[key]["source_sha256"] != source_hashes["latvia"]:
            raise ValueError(f"{key} source hash mismatch")
    if data["scotland_probe"]["source_sha256"] != source_hashes["scotland"]:
        raise ValueError("Scotland probe source hash mismatch")

    latvia_probes = {
        row["event_id"]: row
        for key in ("latvia_accepted_probe", "latvia_withheld_probe")
        for row in data[key]["cases"]
    }
    latvia_cases = []
    for review in data["latvia_ledger"]["reviews"]:
        short_id = review["candidate_id"].split("-")[-1]
        probe = latvia_probes[short_id]
        if review["source_time_s"] != probe["crossing_time_s"]:
            raise ValueError(f"Latvia crossing time mismatch: {short_id}")
        latvia_cases.append(
            {
                "id": review["candidate_id"],
                "source_class": review["source_pixel_class"],
                "time_s": probe["crossing_time_s"],
                "point_px": probe["crossing_point_px"],
            }
        )

    scotland_classes = {
        row["candidate_id"]: row["crossing_source_class"]
        for row in data["scotland_classes"]["rows"]
    }
    scotland_cases = [
        {
            "id": row["event_id"],
            "source_class": scotland_classes[row["event_id"]],
            "time_s": row["crossing_time_s"],
            "point_px": row["crossing_point_px"],
        }
        for row in data["scotland_probe"]["cases"]
    ]
    rows = {}
    fps = {}
    for name, cases in (("latvia", latvia_cases), ("scotland", scotland_cases)):
        rows[name], fps[name] = measure(sources[name], cases)
    output = {
        "status": "selected_same_agent_negative_transfer_diagnostic_not_throw_validation",
        "configuration": {
            "patch_width_px": PATCH_WIDTH,
            "patch_height_px": PATCH_HEIGHT,
            "patch_anchor": "top_centered_on_tracked_crossing_pixel",
            "grayscale_below": DARK_GRAY_BELOW,
            "exploratory_cut_from_latvia": LATVIA_EXPLORATORY_CUT,
        },
        "source_sha256": source_hashes,
        "input_sha256": {key: digest(path) for key, path in inputs.items()},
        "runner_sha256": digest(Path(__file__)),
        "fps": fps,
        "cases": rows,
        "limitations": [
            "Cases were prediction-targeted and reviewed by the development agent, not independently selected throw labels.",
            "A crossing source class describes a pixel, not an entire delivery event.",
            "The Latvia exploratory cut is evaluated on Scotland unchanged and is not promoted as a filter.",
            "Darkness can arise from players, wheelchairs, rink markings, lighting, or stone occlusion.",
        ],
    }
    destination = ARTIFACT / "CROSSING-DARKNESS-TRANSFER.json"
    destination.write_text(json.dumps(output, indent=2, allow_nan=False) + "\n")
    print(destination.relative_to(ROOT))


if __name__ == "__main__":
    main()
