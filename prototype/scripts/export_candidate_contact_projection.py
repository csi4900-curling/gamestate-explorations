"""Project guarded three-frame stone-body bottom proxies through conditional H."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
sys.path.insert(0, str(ROOT / "prototype/scripts"))
from audit_split_panel_freeze import normalized_split_frame
from candidate_contact_projection import stable_body_bottom
from vision_core import project
from wide_view_ground_contact import contact_below_cap


def digest(path):
    h = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--calibrations", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    calibrations = json.loads(args.calibrations.read_text())
    video_hash = digest(args.video)
    if video_hash != calibrations["source_sha256"]:
        parser.error("Source and calibration fingerprints differ")
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        parser.error("Cannot open source video")
    fps = cap.get(cv2.CAP_PROP_FPS)
    rows = []
    try:
        for candidate in calibrations["rows"]:
            if candidate["status"] != "conditional_image_evidence_supported":
                rows.append(
                    {
                        "candidate_id": candidate["candidate_id"],
                        "status": "abstain_no_conditional_plane_calibration",
                        "cap_results": [],
                        "simulation_ready": False,
                    }
                )
                continue
            images = []
            for t in candidate["sample_times_s"]:
                cap.set(cv2.CAP_PROP_POS_FRAMES, round(t * fps))
                ok, frame = cap.read()
                if not ok:
                    raise RuntimeError(f"Cannot decode source {t}s")
                images.append(normalized_split_frame(frame))
            H = np.asarray(candidate["conditional_plane_H"])
            results = []
            for proposal in candidate["cap_center_plane_projections"]:
                contact_samples = [
                    contact_below_cap(image, proposal["cap_pixel_center"]) for image in images
                ]
                stable, status = stable_body_bottom(contact_samples)
                result = {
                    "local_observation_id": proposal["local_observation_id"],
                    "colour": proposal["colour"],
                    "status": status,
                    "three_frame_contact_samples": contact_samples,
                    "stone_ground_contact_verified": False,
                    "metric_accuracy_validated": False,
                }
                if stable is not None:
                    point = stable["body_bottom_pixel_median"]
                    world = project(H, [point])[0]
                    cap_world = proposal["cap_center_projected_as_if_on_ice_plane_m"]
                    result.update(stable)
                    result["body_bottom_proxy_plane_projection_m"] = [
                        round(float(value), 4) for value in world
                    ]
                    result["cap_to_body_proxy_projected_shift_m"] = round(
                        float(np.linalg.norm(world - cap_world)), 4
                    )
                results.append(result)
            rows.append(
                {
                    "candidate_id": candidate["candidate_id"],
                    "status": "conditional_body_bottom_proxy_audit",
                    "sample_times_s": candidate["sample_times_s"],
                    "cap_results": results,
                    "metric_accuracy_validated": False,
                    "complete_board_verified": False,
                    "simulation_ready": False,
                }
            )
    finally:
        cap.release()
    status_counts = Counter(result["status"] for row in rows for result in row["cap_results"])
    result = {
        "status": "conditional_body_bottom_plane_projection_not_physical_game_state",
        "source_sha256": video_hash,
        "calibrations_sha256": digest(args.calibrations),
        "contact_code_sha256": digest(ROOT / "prototype/wide_view_ground_contact.py"),
        "stability_code_sha256": digest(ROOT / "prototype/candidate_contact_projection.py"),
        "frame_normalization_code_sha256": digest(
            ROOT / "prototype/scripts/audit_split_panel_freeze.py"
        ),
        "runner_sha256": digest(Path(__file__)),
        "candidate_count": len(rows),
        "cap_status_counts": dict(status_counts),
        "rows": rows,
        "limitations": [
            "A neutral-body lower edge can be occluded or confused with nearby rink pixels.",
            "Repeated body-bottom pixels are a source-image proxy, not verified ice contact.",
            "The source-specific plane calibration lacks independently validated metre accuracy.",
            "A cap/body projection difference shows sensitivity to pixel height, not corrected physical accuracy.",
            "No complete board, persistent stone identity or simulation-ready state is inferred.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"candidates": len(rows), "cap_statuses": result["cap_status_counts"]}))


if __name__ == "__main__":
    main()
