"""Audit the limited overhead coverage after Norway end-one final delivery."""

from hashlib import sha256
import json
from math import dist
from pathlib import Path
import sys

import cv2


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from prototype.temporal_board_state import stable_board_stones
from prototype.video_board_observation_v2 import detect_board_stones, detect_overhead_house


VIDEO = ROOT / "validation/throw-event-benchmark/paralympics-2022-canada-norway/source.mp4"
SOURCE_SCAN = ROOT / "validation/official-shot-sequence/norway-end1-source-video-partial-boards-first.json"
OUTPUT = ROOT / "validation/official-shot-sequence/norway-end1-final-board-visibility-first.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first final-board visibility audit")
    scan = json.loads(SOURCE_SCAN.read_text())
    if digest(VIDEO) != scan["source_video_sha256"]:
        raise SystemExit("Source video differs from end-one scan")
    cap = cv2.VideoCapture(str(VIDEO))
    if not cap.isOpened():
        raise RuntimeError("Cannot open Norway source video")
    fps = cap.get(cv2.CAP_PROP_FPS)
    frames = []
    try:
        for second in range(1217, 1265):
            cap.set(cv2.CAP_PROP_POS_FRAMES, round(second * fps))
            ok, frame = cap.read()
            if not ok:
                raise RuntimeError(f"Frame decode failed at {second}s")
            house = detect_overhead_house(frame)
            if house is None:
                continue
            house = dict(house)
            if house["delivery_side"] == "uncertain":
                house["delivery_side"] = scan["inferred_delivery_side"]
            if house["delivery_side"] != "top":
                continue
            stones = detect_board_stones(frame, house)
            frames.append({"time_s": float(second), "house_center_px": house["center_px"],
                           "outer_radius_px": house["outer_radius_px"],
                           "stones": [{"colour": stone["colour"],
                                       "lateral_house_radii": stone["canonical_lateral_house_radii"],
                                       "longitudinal_house_radii": stone["longitudinal_house_radii"]}
                                      for stone in stones]})
    finally:
        cap.release()
    observation_rows = [{"time_s": frame["time_s"],
                         "stones": [{"colour": stone["colour"],
                                     "canonical_lateral_house_radii": stone["lateral_house_radii"],
                                     "longitudinal_house_radii": stone["longitudinal_house_radii"]}
                                    for stone in frame["stones"]]}
                        for frame in frames]
    stable = stable_board_stones(observation_rows)
    selected = []
    for frame in frames:
        candidates = [stone for stone in frame["stones"]
                      if stone["colour"] == "yellow" and stone["lateral_house_radii"] > 1.0]
        if frame["time_s"] in (1222.0, 1223.0, 1224.0, 1225.0) and candidates:
            selected.append({"time_s": frame["time_s"],
                             "position_house_radii": [
                                 max(candidates, key=lambda stone: stone["lateral_house_radii"])["lateral_house_radii"],
                                 max(candidates, key=lambda stone: stone["lateral_house_radii"])["longitudinal_house_radii"]]})
    if [row["time_s"] for row in selected] != [1222.0, 1223.0, 1224.0, 1225.0]:
        raise RuntimeError("Expected moving-yellow diagnostic samples unavailable")
    output = {
        "status": "source_only_final_board_visibility_and_moving_yellow_diagnostic",
        "source_video_sha256": digest(VIDEO),
        "source_scan_sha256": digest(SOURCE_SCAN),
        "house_detector_sha256": digest(ROOT / "prototype/video_board_observation_v2.py"),
        "stability_code_sha256": digest(ROOT / "prototype/temporal_board_state.py"),
        "runner_sha256": digest(Path(__file__)),
        "sample_interval_s": [1217, 1265],
        "sample_rate_hz": 1,
        "overhead_frame_count": len(frames),
        "overhead_frame_times_s": [frame["time_s"] for frame in frames],
        "last_overhead_frame_s": frames[-1]["time_s"] if frames else None,
        "stable_partial_board": stable,
        "selected_yellow_motion_hypothesis": selected,
        "selected_yellow_endpoint_displacement_house_radii": round(dist(
            selected[0]["position_house_radii"], selected[-1]["position_house_radii"]), 3),
        "frames": frames,
        "limitations": [
            "The yellow path was selected after inspecting this source; it is a within-shot motion diagnostic, not independently verified stone identity.",
            "No overhead house is available after 1225 s in the scanned interval, so the final settled board is not observed.",
            "The stable-board rule intentionally withholds stones visible only briefly or still moving.",
        ],
    }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n")
    print({"overhead_frame_times_s": output["overhead_frame_times_s"],
           "stable_stones": len(stable),
           "moving_yellow_displacement_house_radii": output["selected_yellow_endpoint_displacement_house_radii"]})


if __name__ == "__main__":
    main()
