"""Reject a simple cross-match ellipse transfer with a held-out rink line."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
sys.path.insert(0, str(ROOT / "prototype/scripts"))
from audit_split_panel_freeze import normalized_split_frame
from house_affine_transfer_audit import affine_line_residual, summarize_residuals, transverse_line_y
from split_house_ellipse_v2 import fit_house_ellipse


def digest(path):
    h = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference-frame", type=Path, required=True)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--ellipse-observations", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    observations = json.loads(args.ellipse_observations.read_text())
    video_hash = digest(args.video)
    if video_hash != observations["source_sha256"]:
        parser.error("Source video and ellipse observations differ")
    reference_frame = cv2.imread(str(args.reference_frame))
    if reference_frame is None:
        parser.error("Cannot open reference frame")
    reference_frame = normalized_split_frame(reference_frame)
    reference_ellipse = fit_house_ellipse(reference_frame)
    if reference_ellipse is None:
        parser.error("Cannot fit reference house ellipse")
    reference_line = transverse_line_y(reference_frame, reference_ellipse["center_px"][1])
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        parser.error("Cannot open target video")
    fps = cap.get(cv2.CAP_PROP_FPS)
    rows = []
    try:
        for item in observations["rows"]:
            if item["observation_status"] != "stable_image_paint_ellipse":
                continue
            t = item["sample_times_s"][1]
            frame_number = round(t * fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            ok, frame = cap.read()
            if not ok:
                raise RuntimeError(f"Cannot decode target frame at {t}s")
            target_ellipse = item["stable_image_house_ellipse"]
            observed_line = transverse_line_y(
                normalized_split_frame(frame), target_ellipse["center_px"][1]
            )
            rows.append(
                {
                    "candidate_id": item["candidate_id"],
                    "sample_time_s": t,
                    "decoded_frame_index": frame_number,
                    "line_edge_strength": observed_line["mean_vertical_edge_strength"],
                    **affine_line_residual(
                        reference_ellipse,
                        reference_line["line_y_px"],
                        target_ellipse,
                        observed_line["line_y_px"],
                    ),
                }
            )
    finally:
        cap.release()
    result = {
        "status": "source_hashed_heldout_image_line_calibration_transfer_audit",
        "source_sha256": video_hash,
        "reference_frame_sha256": digest(args.reference_frame),
        "ellipse_observations_sha256": digest(args.ellipse_observations),
        "reference_house_ellipse": reference_ellipse,
        "reference_transverse_line": reference_line,
        "model_code_sha256": digest(ROOT / "prototype/house_affine_transfer_audit.py"),
        "ellipse_code_sha256": digest(ROOT / "prototype/split_house_ellipse_v2.py"),
        "frame_normalization_code_sha256": digest(
            ROOT / "prototype/scripts/audit_split_panel_freeze.py"
        ),
        "runner_sha256": digest(Path(__file__)),
        "summary": summarize_residuals(rows),
        "rows": rows,
        "limitations": [
            "The transverse marking is a visual rink-line proxy, not a surveyed point.",
            "Its search band and 4-pixel diagnostic threshold were selected on these exposed sources.",
            "A line check that passes would still not establish a full homography or metric accuracy.",
            "No cap positions are promoted to rink metres by this audit.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result["summary"]))


if __name__ == "__main__":
    main()
