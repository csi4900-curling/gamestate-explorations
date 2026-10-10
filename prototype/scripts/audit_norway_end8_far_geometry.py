"""Diagnose far-house residuals in four source-reviewed end-eight boards."""

from hashlib import sha256
import json
from math import hypot
from pathlib import Path
import sys

import cv2
import numpy as np
from scipy.optimize import linear_sum_assignment


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/official-shot-sequence"
SCAN = BASE / "norway-full-candidate-post-counter-long-window-boards-v4.json"
SCORE = BASE / "norway-full-post-counter-long-window-board-postscore-v4.json"
OFFICIAL = BASE / "pwg2022-canada-norway-official-boards.json"
VIDEO = ROOT / "validation/throw-event-benchmark/paralympics-2022-canada-norway/source.mp4"
OUTPUT = BASE / "norway-end8-far-house-residual-audit-first.json"
IMAGE = BASE / "norway-end8-far-house-source-frames.jpg"
CASES = [
    ("PREL001501-E08-S10", "S591", "S594", [8107.0, 8131.0]),
    ("PREL001501-E08-S11", "S599", "S602", [8207.4, 8211.4]),
    ("PREL001501-E08-S12", "S603", "S606", [8262.4, 8278.4]),
    ("PREL001501-E08-S13", "S610", "S613", [8349.4, 8353.4]),
]


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    if OUTPUT.exists() or IMAGE.exists():
        raise SystemExit("First end-eight far-house audit already exists")
    scan = json.loads(SCAN.read_text())
    score = json.loads(SCORE.read_text())
    official = json.loads(OFFICIAL.read_text())
    if len({scan["source_video_sha256"], official["source_video_sha256"], digest(VIDEO)}) != 1:
        raise SystemExit("Source video hashes disagree")
    if score["input_sha256"]["source_scan"] != digest(SCAN):
        raise SystemExit("Score/source scan hash conflict")
    by_candidate = {row["shot_id"]: row for row in scan["rows"]}
    by_official = {shot["official_shot_id"]: shot for end in official["ends"]
                   for shot in end["shots"]}
    cap = cv2.VideoCapture(str(VIDEO))
    if not cap.isOpened():
        raise SystemExit("Cannot open source video")
    output_cases = []
    frame_rows = []
    try:
        for official_id, candidate_id, camera_id, times in CASES:
            candidate = by_candidate[candidate_id]
            group = next(group for group in candidate["camera_shot_boards"]
                         if group["camera_shot_id"] == camera_id)
            shot = by_official[official_id]
            if shot["house_center_px"][1] != 440 or group["detected_delivery_side"] != "top":
                raise SystemExit("Expected top-oriented source/PDF cases changed")
            video_stones = group["stable_image_relative_stones"]
            official_stones = shot["stones"]
            if len(video_stones) != len(official_stones):
                raise SystemExit("Expected equal stone counts for diagnostic pairs")
            pairs = []
            for colour in ("red", "yellow"):
                observed = [stone for stone in video_stones if stone["colour"] == colour]
                reference = [stone for stone in official_stones if stone["colour"] == colour]
                if len(observed) != len(reference):
                    raise SystemExit("Per-colour count changed")
                cost = np.asarray([[hypot(a["image_house_radius_coordinates"][0] - b["house_radius_coordinates"][0],
                                          a["image_house_radius_coordinates"][1] - b["house_radius_coordinates"][1])
                                    for b in reference] for a in observed])
                vi, oi = linear_sum_assignment(cost)
                for i, j in zip(vi, oi):
                    a = observed[int(i)]["image_house_radius_coordinates"]
                    b = reference[int(j)]["house_radius_coordinates"]
                    pairs.append({"colour": colour,
                                  "video_image_house_radii": a,
                                  "official_diagram_house_radii": b,
                                  "delta_video_minus_official": [round(a[0] - b[0], 4),
                                                                 round(a[1] - b[1], 4)],
                                  "distance_house_radii": round(float(cost[i, j]), 4),
                                  "range_band": "far_above_house" if b[1] < -1.5 else
                                                "near_house" if abs(b[1]) <= 1.25 else "intermediate"})
            output_cases.append({"official_shot_id": official_id,
                                 "candidate_id": candidate_id,
                                 "post_camera_shot_id": camera_id,
                                 "source_observation_interval_s": group["observation_interval_s"],
                                 "source_frame_times_s": times,
                                 "pair_count": len(pairs), "pairs": pairs})
            frames = []
            for t in times:
                cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
                ok, frame = cap.read()
                if not ok:
                    raise RuntimeError(f"Cannot read source frame at {t}")
                frame = cv2.resize(frame, (640, 360), interpolation=cv2.INTER_AREA)
                cv2.putText(frame, f"{official_id[-7:]} {t:.1f}s", (8, 340),
                            cv2.FONT_HERSHEY_SIMPLEX, .7, (255, 255, 255), 2)
                frames.append(frame)
            frame_rows.append(np.hstack(frames))
    finally:
        cap.release()
    if not cv2.imwrite(str(IMAGE), np.vstack(frame_rows), [cv2.IMWRITE_JPEG_QUALITY, 90]):
        raise RuntimeError("Could not save source review montage")
    far = [pair for case in output_cases for pair in case["pairs"]
           if pair["range_band"] == "far_above_house"]
    near = [pair for case in output_cases for pair in case["pairs"]
            if pair["range_band"] == "near_house"]
    def summarize(rows):
        return {"pair_count": len(rows),
                "mean_absolute_longitudinal_delta_house_radii": round(
                    sum(abs(row["delta_video_minus_official"][1]) for row in rows) / len(rows), 4),
                "mean_signed_longitudinal_delta_house_radii": round(
                    sum(row["delta_video_minus_official"][1] for row in rows) / len(rows), 4)}
    result = {
        "status": "retrospective_selected_end8_far_house_geometry_diagnostic_not_independent_accuracy",
        "source_video_sha256": digest(VIDEO),
        "input_sha256": {"source_scan": digest(SCAN), "postscore": digest(SCORE),
                         "official_diagrams": digest(OFFICIAL)},
        "runner_sha256": digest(Path(__file__)),
        "source_frames_sha256": digest(IMAGE),
        "selection": "Four end-eight earliest source groups were selected after observing their postscore mismatches; no blind holdout.",
        "far_band": summarize(far),
        "near_band": summarize(near),
        "cases": output_cases,
        "limitations": [
            "Same-colour minimum-cost pairs are diagnostic correspondences, not proven persistent physical IDs.",
            "Repeated far stones across four shots are not independent samples.",
            "Image-house-radius coordinates assume one apparent radius; perspective and PDF diagram quantization are not independently calibrated.",
            "A longitudinal bias suggests a geometry problem but does not establish its exact cause or physical centimetre error.",
        ],
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print(result["far_band"], result["near_band"])


if __name__ == "__main__":
    main()
