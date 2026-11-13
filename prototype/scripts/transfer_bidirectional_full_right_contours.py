"""Post-review right-panel contour transfer on three selected yellow episodes."""

from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from scripts.continue_yellow_by_contour import continue_path, yellow_contours
from yellow_contour_bidirectional import yellow_contours_in_roi

BASE = ROOT / "validation/throw-event-benchmark"
EPISODES = (
    BASE / "layout-router/full-2024-coverage/yellow-bidirectional-motion-episodes-postscore.json"
)
OUTPUT = (
    BASE
    / "layout-router/full-2024-coverage/yellow-full-right-panel-contour-transfer-postreview-v2.json"
)
EXPANDED_ROI = (990, 0, 1890, 1080)
SOURCES = {
    "korea": (ROOT / "prototype/continuous/clip.mp4", 2260),
    "slovakia": (BASE / "canada-slovakia-2024/source-1080p-1650-2760.mp4", 1650),
    "estonia": (BASE / "canada-estonia-2024/source-1080p-1650-2760.mp4", 1650),
}


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def scan(source, offset_s, start_s, stop_s):
    cap = cv2.VideoCapture(str(source), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened() or cap.get(cv2.CAP_PROP_FPS) != 30:
        raise RuntimeError("Cannot open expected 30-fps video")
    rows = []
    try:
        cap.set(cv2.CAP_PROP_POS_FRAMES, (start_s - offset_s) * 30)
        for t in range(start_s, stop_s + 1):
            ok, frame = cap.read()
            if not ok or frame.shape[:2] != (1080, 1920):
                raise RuntimeError(f"Cannot decode {source} at {t}")
            expanded = yellow_contours_in_roi(frame, EXPANDED_ROI)
            frozen = yellow_contours(frame)
            legacy_region = [
                p
                for p in expanded
                if 990 <= p["center_1080p_px"][0] <= 1890 and 400 <= p["center_1080p_px"][1] <= 970
            ]
            if legacy_region != frozen:
                raise AssertionError(f"Contour thresholds changed at {t}")
            rows.append({"source_time_s": t, "raw_yellow_handle_contours": expanded})
            if t < stop_s:
                for _ in range(29):
                    if not cap.grab():
                        raise RuntimeError(f"Cannot advance from {t}")
    finally:
        cap.release()
    return rows


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first expanded-region transfer")
    data = json.loads(EPISODES.read_text())
    rows = []
    source_hashes = {}
    for episode in data["rows"]:
        motion = episode["motion_episode"]
        if motion is None:
            continue
        name = episode["source"]
        source, offset = SOURCES[name]
        source_hashes[name] = digest(source)
        previous = data["input_sha256"][name]
        first_path = {
            "korea": BASE / "canada-korea-2024/yellow-handoff-generic-regression.json",
            "slovakia": BASE / "canada-slovakia-2024/yellow-handoff-1990-2070-development.json",
            "estonia": BASE / "canada-estonia-2024/yellow-contour-1720-1800-first-transfer.json",
        }[name]
        first = json.loads(first_path.read_text())
        if (
            digest(first_path) != previous["first_pass_sha256"]
            or first["target_video_sha256"] != source_hashes[name]
        ):
            raise ValueError(f"Source or frozen episode lineage changed: {name}")
        seed_points = episode["continuation"]["points"][:]
        seed_end = motion["moving_run_interval_s"][1]
        seed_points = [point for point in seed_points if point["time_s"] <= seed_end]
        seed = {
            "diagnostic_path_id": episode["body_path_id"],
            "first_observed_s": seed_points[0]["time_s"],
            "last_observed_s": seed_end,
            "points": seed_points,
        }
        scan_rows = scan(source, offset, seed_end + 1, seed_end + 20)
        joined = continue_path(seed, scan_rows)
        last = joined["points"][-1]
        near_edge = last["center_1080p_px"][1] >= 1020
        rows.append(
            {
                "source": name,
                "body_path_id": episode["body_path_id"],
                "motion_direction_image_y": motion["direction"],
                "observed_motion_onset_bracket_s": motion["motion_onset_observation_bracket_s"],
                "expanded_ice_roi_1080p": EXPANDED_ROI,
                "scan_interval_s": [seed_end + 1, seed_end + 20],
                "expanded_contour_count": sum(
                    len(r["raw_yellow_handle_contours"]) for r in scan_rows
                ),
                "path": joined,
                "last_linked_near_bottom_boundary": near_edge,
                "physical_stop_verified": False,
                "physical_stone_identity_verified": False,
            }
        )
    output = {
        "status": "postreview_direction_agnostic_expanded_right_contour_transfer_not_f1",
        "source_sha256": source_hashes,
        "episodes_sha256": digest(EPISODES),
        "frozen_contour_code_sha256": digest(
            ROOT / "prototype/scripts/continue_yellow_by_contour.py"
        ),
        "expanded_contour_code_sha256": digest(ROOT / "prototype/yellow_contour_bidirectional.py"),
        "runner_sha256": digest(Path(__file__)),
        "rows": rows,
        "limitations": [
            "Expanded region was chosen after Estonia source review; all three intervals were exposed.",
            "The unchanged linker can select another yellow object when several are nearby.",
            "Image stillness is not physical settle and panel exit is right-censored.",
            "Three selected windows do not measure full-match precision, recall or F1.",
        ],
    }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n")
    print(
        json.dumps(
            [
                (
                    r["source"],
                    r["path"]["points"][-1]["time_s"],
                    r["path"]["image_motion_interpretation"]["visual_stop_bracket_s"],
                    r["last_linked_near_bottom_boundary"],
                )
                for r in rows
            ]
        )
    )


if __name__ == "__main__":
    main()
