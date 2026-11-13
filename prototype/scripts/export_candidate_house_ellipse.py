"""Add guarded image-relative house coordinates to partial cap observations."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
sys.path.insert(0, str(ROOT / "prototype/scripts"))
from audit_split_panel_freeze import normalized_split_frame
from split_house_ellipse_v2 import fit_house_ellipse, normalized_cap_image_xy, stable_house_ellipse


def digest(path):
    h = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def export_rows(cap, fps, candidates):
    rows = []
    for candidate in candidates:
        observation = candidate["post_candidate_image_observation"]
        if observation["status"] != "partial_stable_colour_cap_proposals":
            continue
        times = observation["sample_times_s"]
        if len(times) != 3:
            raise ValueError("Usable cap observation requires three source frames")
        ellipses = []
        for t in times:
            frame_number = round(t * fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            ok, frame = cap.read()
            if not ok:
                raise RuntimeError(f"Cannot decode source time {t}")
            ellipses.append(fit_house_ellipse(normalized_split_frame(frame)))
        stable, status = stable_house_ellipse(ellipses)
        caps = (
            []
            if stable is None
            else [
                {
                    "local_observation_id": item["local_observation_id"],
                    "colour": item["colour"],
                    "cap_image_xy_house_ellipse_radii": normalized_cap_image_xy(
                        stable, item["pixel_center"]
                    ),
                    "physical_stone_identity_verified": False,
                    "ground_contact_position_verified": False,
                }
                for item in observation["stable_cap_proposals"]
            ]
        )
        rows.append(
            {
                "candidate_id": candidate["candidate_id"],
                "sample_times_s": times,
                "observation_status": status,
                "sample_ellipses": ellipses,
                "stable_image_house_ellipse": stable,
                "normalized_cap_proposals": caps,
                "metric_rink_coordinates_verified": False,
                "complete_board_verified": False,
                "simulation_ready": False,
            }
        )
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--handoff", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    handoff = json.loads(args.handoff.read_text())
    video_hash = digest(args.video)
    if video_hash != handoff["source_sha256"]:
        parser.error("Source and handoff fingerprints differ")
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        parser.error("Cannot open source video")
    try:
        rows = export_rows(cap, cap.get(cv2.CAP_PROP_FPS), handoff["ordered_candidates"])
    finally:
        cap.release()
    result = {
        "status": "candidate_cap_image_house_relative_coordinates_not_metric_game_state",
        "source_sha256": video_hash,
        "handoff_sha256": digest(args.handoff),
        "paint_mask_code_sha256": digest(ROOT / "prototype/split_house_reference.py"),
        "model_code_sha256": digest(ROOT / "prototype/split_house_ellipse_v2.py"),
        "frame_normalization_code_sha256": digest(
            ROOT / "prototype/scripts/audit_split_panel_freeze.py"
        ),
        "runner_sha256": digest(Path(__file__)),
        "normalized_coordinate_unit": "cap_pixel_divided_by_image_ellipse_semiaxis",
        "fitted_candidate_count": len(rows),
        "observation_status_counts": dict(Counter(row["observation_status"] for row in rows)),
        "rows": rows,
        "limitations": [
            "Ellipse thresholds were adjusted after inspecting Latvia and Italy sources; this is development evidence.",
            "Paint contour fitting is not a camera homography or surveyed rink calibration.",
            "Cap centers are above the ice and do not equal stone contact positions.",
            "Only earlier usable partial cap observations are fitted; missing stones stay missing.",
            "No complete game state, stone identity or physical simulation is inferred.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"rows": len(rows), "statuses": result["observation_status_counts"]}))


if __name__ == "__main__":
    main()
