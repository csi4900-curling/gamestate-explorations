"""Recheck a donor H on every target frame before conditional reuse."""

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
from registered_house_calibration import alignment_supported, nearest_donor
from right_view_house_alignment import alignment_probe, blue_house_mask
from scripts.export_source_house_calibration import temporal_check


def digest(path):
    h = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("video", "handoff", "ellipses", "calibrations", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    handoff = json.loads(args.handoff.read_text())
    ellipses = json.loads(args.ellipses.read_text())
    calibrations = json.loads(args.calibrations.read_text())
    source_hash = digest(args.video)
    if (
        source_hash != handoff["source_sha256"]
        or source_hash != ellipses["source_sha256"]
        or source_hash != calibrations["source_sha256"]
        or calibrations["input_sha256"]["handoff"] != digest(args.handoff)
        or calibrations["input_sha256"]["ellipses"] != digest(args.ellipses)
    ):
        parser.error("Source, ellipse, handoff or calibration provenance differs")
    candidates = {row["candidate_id"]: row for row in handoff["ordered_candidates"]}
    if len(candidates) != len(handoff["ordered_candidates"]):
        raise ValueError("Duplicate candidate ID")
    accepted = [
        row
        for row in calibrations["rows"]
        if row["status"] == "conditional_image_evidence_supported"
    ]
    first_by_id = {row["candidate_id"]: row for row in calibrations["rows"]}
    ellipse_by_id = {
        row["candidate_id"]: row
        for row in ellipses["rows"]
        if row["observation_status"] == "stable_image_paint_ellipse"
    }
    if set(first_by_id) != set(ellipse_by_id):
        raise ValueError("Calibration and stable ellipse rows differ")
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        parser.error("Cannot open source video")
    fps = cap.get(cv2.CAP_PROP_FPS)
    frames = {}
    try:
        for candidate_id, item in ellipse_by_id.items():
            images = []
            for t in item["sample_times_s"]:
                cap.set(cv2.CAP_PROP_POS_FRAMES, round(t * fps))
                ok, image = cap.read()
                if not ok:
                    raise RuntimeError(f"Cannot decode source {t}s")
                images.append(normalized_split_frame(image))
            frames[candidate_id] = images
    finally:
        cap.release()
    masks = {candidate_id: blue_house_mask(images[1]) for candidate_id, images in frames.items()}
    rows = []
    for candidate_id, item in ellipse_by_id.items():
        original = first_by_id[candidate_id]
        base = {
            "candidate_id": candidate_id,
            "original_fit_status": original["status"],
            "metric_accuracy_validated": False,
            "complete_board_verified": False,
            "simulation_ready": False,
        }
        if original["status"] == "conditional_image_evidence_supported":
            rows.append(
                {
                    **base,
                    "status": "original_conditional_fit_retained",
                    "donor_candidate_id": None,
                    "conditional_plane_H": original["conditional_plane_H"],
                }
            )
            continue
        donor = nearest_donor(item, accepted, candidates)
        if donor is None:
            rows.append(
                {
                    **base,
                    "status": "abstain_no_same_route_donor",
                    "donor_candidate_id": None,
                    "conditional_plane_H": None,
                }
            )
            continue
        donor_id = donor["candidate_id"]
        try:
            alignment = alignment_probe(masks[donor_id], masks[candidate_id])
            supported = alignment_supported(alignment)
        except ValueError:
            alignment = None
            supported = False
        if not supported:
            rows.append(
                {
                    **base,
                    "status": "abstain_house_image_alignment",
                    "donor_candidate_id": donor_id,
                    "painted_house_alignment": alignment,
                    "conditional_plane_H": None,
                }
            )
            continue
        H = np.asarray(donor["conditional_plane_H"])
        checks = [
            temporal_check(frame, H, ellipse)
            if ellipse is not None
            else {"passes": False, "reason": "missing_house_ellipse"}
            for frame, ellipse in zip(frames[candidate_id], item["sample_ellipses"])
        ]
        passed = all(check["passes"] for check in checks)
        rows.append(
            {
                **base,
                "status": (
                    "conditional_registered_donor_fit"
                    if passed
                    else "abstain_target_geometry_checks_failed"
                ),
                "donor_candidate_id": donor_id,
                "painted_house_alignment": alignment,
                "three_target_frame_checks": checks,
                "conditional_plane_H": H.tolist() if passed else None,
            }
        )
    result = {
        "status": "strict_same_route_house_calibration_reuse_not_metric_validation",
        "source_sha256": source_hash,
        "input_sha256": {
            "handoff": digest(args.handoff),
            "ellipses": digest(args.ellipses),
            "calibrations": digest(args.calibrations),
        },
        "model_code_sha256": digest(ROOT / "prototype/registered_house_calibration.py"),
        "source_fit_check_code_sha256": digest(
            ROOT / "prototype/scripts/export_source_house_calibration.py"
        ),
        "house_alignment_code_sha256": digest(ROOT / "prototype/right_view_house_alignment.py"),
        "runner_sha256": digest(Path(__file__)),
        "candidate_count": len(rows),
        "status_counts": dict(Counter(row["status"] for row in rows)),
        "rows": rows,
        "limitations": [
            "A donor is reused only within the same candidate origin and routed interval.",
            "Three sampled frames cannot prove an unchanged camera between or beyond those frames.",
            "The zero-shift house mask and ring/hog checks are image evidence, not surveyed metric accuracy.",
            "No stone contact, complete board or simulation-ready event is inferred.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"candidates": len(rows), "statuses": result["status_counts"]}))


if __name__ == "__main__":
    main()
