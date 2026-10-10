"""Produce a lossless camera-motion sidecar for source-hashed span proposals."""

import argparse
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256  # noqa: E402
from candidate_camera_motion import measure_candidate  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--preflight", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve prior results")
    digest = file_sha256(args.video)
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    if digest == reserved["source_sha256"]:
        parser.error("Reserved source cannot be used for development motion audits")
    raw = json.loads(args.raw.read_text())
    preflight = json.loads(args.preflight.read_text())
    if raw["source_sha256"] != digest or preflight["source_sha256"] != digest:
        raise ValueError("Source hash mismatch")
    if (raw["source_interval_s"][0] < preflight["source_interval_s"][0]
            or raw["source_interval_s"][1] > preflight["source_interval_s"][1]):
        raise ValueError("Raw interval outside preflight")
    if (raw["model_sha256"] != file_sha256(ROOT / "prototype/span_passage_detection.py")
            or raw["baseline_sha256"] != file_sha256(ROOT / "prototype/throw_detection.py")):
        raise ValueError("Raw proposal model lineage differs")
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG,
                           [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        raise ValueError("Source unreadable")
    fps = cap.get(cv2.CAP_PROP_FPS)

    def frame_at(time_s):
        cap.set(cv2.CAP_PROP_POS_FRAMES, round(time_s * fps))
        ok, frame = cap.read()
        if not ok:
            raise ValueError(f"Source frame unreadable at {time_s}")
        return frame

    try:
        rows = [measure_candidate(event, preflight, digest, frame_at)
                for event in raw["events"]]
    finally:
        cap.release()
    if len(rows) != len({row["id"] for row in rows}):
        raise ValueError("Duplicate candidate IDs")
    payload = {
        "status": "candidate_camera_motion_evidence_not_throw_truth",
        "source_id": raw["source_id"], "source_sha256": digest,
        "source_interval_s": raw["source_interval_s"],
        "input_sha256": {"raw": file_sha256(args.raw),
                         "preflight": file_sha256(args.preflight)},
        "code_sha256": {
            "candidate": file_sha256(ROOT / "prototype/candidate_camera_motion.py"),
            "router": file_sha256(ROOT / "prototype/layout_camera_motion.py"),
            "lowres_adapter": file_sha256(ROOT / "prototype/lowres_split_panel_camera_registration.py"),
            "split_registration": file_sha256(ROOT / "prototype/split_panel_camera_registration.py"),
            "runner": file_sha256(__file__)},
        "rows": rows,
        "limitations": [
            "Path pixels come from unverified raw cap tracks, not physical stone identities.",
            "Camera-relative displacement is evidence only; this sidecar does not alter event decisions.",
            "A path ending at candidate confirmation does not establish physical release or settle.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps({"candidates": len(rows),
                      "registered": sum(row.get("camera_residual_px") is not None
                                        for row in rows)}))


if __name__ == "__main__":
    main()
