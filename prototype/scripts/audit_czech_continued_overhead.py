"""Check whether early-ROI track continuation exposes the old overhead cue."""

from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.scripts.audit_path_overhead_darkness import overhead_dark_fraction  # noqa: E402

BASE = ROOT / "validation/throw-event-benchmark"
VIDEO = BASE / "canada-czech-2024/source-1080p-full-format270.mp4"
PRIOR = BASE / "canada-czech-2024/overhead-darkness-development-postscore.json"
PATHS = {
    "S96": BASE / "layout-router/camera-motion-integrated-czech24-s96-negative/raw-with-continuation-development.json",
    "S143": BASE / "layout-router/czech24-full-camera-motion-v1/s143-raw-with-continuation-development.json",
}
OUT = BASE / "layout-router/czech24-full-camera-motion-v1/continued-overhead-pilot.json"


def digest(path):
    h = sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def main():
    if OUT.exists():
        raise ValueError("Pilot exists; preserve prior output")
    prior = json.loads(PRIOR.read_text())
    if digest(VIDEO) != prior["high_resolution_source_sha256"] or \
            prior["source_offset_s"] != 0:
        raise ValueError("Aligned high-resolution source differs")
    cap = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG,
                           [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        raise ValueError("Source unreadable")
    fps = cap.get(cv2.CAP_PROP_FPS)
    rows = []
    try:
        for old_id, path in PATHS.items():
            data = json.loads(path.read_text())
            if data["source_sha256"] != prior["source_sha256"]:
                raise ValueError("360p source differs")
            old = next(r for r in prior["rows"] if r["candidate_id"] == old_id)
            event = min(data["events"], key=lambda row: abs(
                row["crossing_time_s"] - (4037.326 if old_id == "S96" else 6374.697)))
            if abs(event["crossing_time_s"] - (
                    4037.326 if old_id == "S96" else 6374.697)) > 0.001:
                raise ValueError("Source candidate did not replay")
            samples = []
            for point in event["continued_track_points"]:
                t = point["time_s"]
                bbox = [round(v * 3) for v in point["bbox"]]
                cap.set(cv2.CAP_PROP_POS_FRAMES, round(t * fps))
                ok, frame = cap.read()
                if not ok:
                    raise ValueError(f"Frame unreadable at {t}")
                fraction = overhead_dark_fraction(frame, bbox)
                samples.append({"source_time_s": t,
                                "video_frame_index": int(cap.get(
                                    cv2.CAP_PROP_POS_FRAMES)) - 1,
                                "bbox_1080p_px": bbox,
                                "overhead_dark_fraction": fraction})
            measured = [s["overhead_dark_fraction"] for s in samples
                        if s["overhead_dark_fraction"] is not None]
            rows.append({
                "full_match_candidate_id": old_id,
                "short_replay_candidate_id": event["id"],
                "crossing_time_s": event["crossing_time_s"],
                "track_point_count": len(samples),
                "measured_count": len(measured),
                "unmeasured_count": len(samples) - len(measured),
                "minimum_measured_dark_fraction": min(measured) if measured else None,
                "maximum_measured_dark_fraction": max(measured) if measured else None,
                "prior_later_positive_patch_minimum": old[
                    "minimum_overhead_dark_fraction"],
                "samples": samples,
            })
    finally:
        cap.release()
    OUT.write_text(json.dumps({
        "status": "continued_early_roi_overhead_development_pilot_not_stone_identity",
        "source_360p_sha256": prior["source_sha256"],
        "source_1080p_sha256": prior["high_resolution_source_sha256"],
        "input_sha256": {"prior_overhead": digest(PRIOR),
                         **{id: digest(path) for id, path in PATHS.items()}},
        "feature_code_sha256": digest(ROOT /
            "prototype/scripts/audit_path_overhead_darkness.py"),
        "runner_sha256": digest(Path(__file__)),
        "rows": rows,
        "limitations": [
            "The two known non-stone paths and feature were selected after source review.",
            "Only early-ROI track continuation is measured; later high-resolution patch-positive samples may belong to a different spatial track interval.",
            "A missing overhead patch or low dark fraction is not evidence of a true stone.",
        ],
    }, indent=2) + "\n")
    print(json.dumps([{k: r[k] for k in (
        "full_match_candidate_id", "measured_count", "unmeasured_count",
        "maximum_measured_dark_fraction",
        "prior_later_positive_patch_minimum")} for r in rows]))


if __name__ == "__main__":
    main()
