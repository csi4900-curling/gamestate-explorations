"""Fit per-candidate rink-plane image geometry with withheld ring and time checks."""

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
from house_affine_transfer_audit import transverse_line_y
from rectification_core import validate_rings
from source_specific_house_calibration import HOG_FROM_TEE_M, REGION, fit_source_house
from split_house_ellipse_v2 import fit_house_ellipse
from vision_core import project


def digest(path):
    h = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_frame(cap, fps, t):
    cap.set(cv2.CAP_PROP_POS_FRAMES, round(t * fps))
    ok, image = cap.read()
    if not ok:
        raise RuntimeError(f"Could not decode source at {t}s")
    return normalized_split_frame(image)


def temporal_check(image, H, ellipse):
    supported, check = validate_rings(image, H, REGION)
    line = transverse_line_y(image, ellipse["center_px"][1])
    hog_world = project(H, [[490, line["line_y_px"]]])[0, 1]
    return {
        "ring_status": check["status"],
        "ring_p95_abs_radial_error_m": check["p95_abs_radial_error_m"],
        "hog_line_y_px": line["line_y_px"],
        "projected_hog_world_y_m": round(float(hog_world), 4),
        "passes": bool(supported and abs(hog_world - HOG_FROM_TEE_M) < 0.25),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "video",
        "handoff",
        "ellipses",
        "reference-frame",
        "reference-calibration",
        "output",
    ):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    handoff = json.loads(args.handoff.read_text())
    ellipses = json.loads(args.ellipses.read_text())
    video_hash = digest(args.video)
    if (
        video_hash != handoff["source_sha256"]
        or video_hash != ellipses["source_sha256"]
        or ellipses["handoff_sha256"] != digest(args.handoff)
    ):
        parser.error("Video, handoff and ellipse evidence differ")
    reference_image = cv2.imread(str(args.reference_frame))
    if reference_image is None:
        parser.error("Cannot read reference frame")
    reference_ellipse = fit_house_ellipse(normalized_split_frame(reference_image))
    if reference_ellipse is None:
        parser.error("Cannot fit reference house ellipse")
    calibration = json.loads(args.reference_calibration.read_text())
    reference_H = calibration["right"]["refined_H"]
    candidates = {row["candidate_id"]: row for row in handoff["ordered_candidates"]}
    if len(candidates) != len(handoff["ordered_candidates"]):
        raise ValueError("Duplicate candidate ID")
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        parser.error("Cannot open source video")
    fps = cap.get(cv2.CAP_PROP_FPS)
    rows = []
    try:
        for item in ellipses["rows"]:
            if item["observation_status"] != "stable_image_paint_ellipse":
                continue
            times = item["sample_times_s"]
            frames = [read_frame(cap, fps, t) for t in times]
            H, fit = fit_source_house(
                frames[1], item["stable_image_house_ellipse"], reference_H, reference_ellipse
            )
            temporal = []
            status = fit["status"]
            if H is not None:
                for frame in (frames[0], frames[2]):
                    ellipse = fit_house_ellipse(frame)
                    temporal.append(
                        temporal_check(frame, H, ellipse)
                        if ellipse is not None
                        else {"passes": False, "reason": "missing_house_ellipse"}
                    )
                if not all(check["passes"] for check in temporal):
                    status = "abstain_temporal_geometry_change"
                    H = None
            caps = []
            if H is not None:
                original = candidates[item["candidate_id"]]["post_candidate_image_observation"][
                    "stable_cap_proposals"
                ]
                caps = [
                    {
                        "local_observation_id": stone["local_observation_id"],
                        "colour": stone["colour"],
                        "cap_pixel_center": stone["pixel_center"],
                        "cap_center_projected_as_if_on_ice_plane_m": [
                            round(float(value), 4)
                            for value in project(H, [stone["pixel_center"]])[0]
                        ],
                        "stone_ground_contact_position_verified": False,
                        "physical_stone_identity_verified": False,
                    }
                    for stone in original
                ]
            rows.append(
                {
                    "candidate_id": item["candidate_id"],
                    "sample_times_s": times,
                    "status": status,
                    "middle_frame_fit": fit,
                    "first_and_last_frame_checks": temporal,
                    "conditional_plane_H": H.tolist() if H is not None else None,
                    "cap_center_plane_projections": caps,
                    "metric_accuracy_validated": False,
                    "complete_board_verified": False,
                    "simulation_ready": False,
                }
            )
    finally:
        cap.release()
    result = {
        "status": "source_specific_house_plane_calibration_proposals_not_game_state",
        "source_sha256": video_hash,
        "input_sha256": {
            "handoff": digest(args.handoff),
            "ellipses": digest(args.ellipses),
            "reference_frame": digest(args.reference_frame),
            "reference_calibration": digest(args.reference_calibration),
        },
        "model_code_sha256": digest(ROOT / "prototype/source_specific_house_calibration.py"),
        "runner_sha256": digest(Path(__file__)),
        "reference_house_ellipse": reference_ellipse,
        "candidate_count": len(rows),
        "status_counts": dict(Counter(row["status"] for row in rows)),
        "rows": rows,
        "limitations": [
            "The reference calibration, edge search, fit regularizers and gates were developed on exposed footage.",
            "Ring paint and hog-line agreement are same-source image checks, not surveyed metric accuracy.",
            "Plane projection of an elevated cap center is not a stone ground-contact position.",
            "The camera may move between three samples or after them; no transform is extrapolated.",
            "No complete board, physical throw, persistent stone identity or simulation-ready event is inferred.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"candidates": len(rows), "statuses": result["status_counts"]}))


if __name__ == "__main__":
    main()
