"""Test whether background registration resolves possible-edit ambiguity."""

from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from camera_relative_motion import estimate_camera_transform

BASE = ROOT / "validation/curlobserver-learned-probe"
SOURCES = {
    "china": (
        ROOT / "validation/throw-event-benchmark/paralympics-2022-canada-china/source.mp4",
        BASE / "china-full-transfer/possible-edits-v1.json",
    ),
    "swiss": (
        ROOT / "validation/throw-event-benchmark/paralympics-2022-sweden-switzerland/source.mp4",
        BASE / "swiss-full-transfer/possible-edits-v1.json",
    ),
}
OUTPUT = BASE / "possible-edit-registration-postscan.json"


def digest(path):
    h = sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first registration audit")
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    source_rows = []
    hashes = {}
    for name, (video, proposals_path) in SOURCES.items():
        proposals = json.loads(proposals_path.read_text())
        source_hash = digest(video)
        if source_hash != proposals["source_sha256"] or source_hash == reserved["source_sha256"]:
            raise ValueError(f"Source fingerprint mismatch: {name}")
        hashes[name] = {"video": source_hash, "possible_edits": digest(proposals_path)}
        capture = cv2.VideoCapture(str(video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
        fps = capture.get(cv2.CAP_PROP_FPS)
        rows = []
        for proposal in proposals["possible_edits_outside_hard_cuts"]:
            frames = []
            for time_s in (
                proposal["time_s"] - 1 / proposals["sample_rate_hz"],
                proposal["time_s"],
            ):
                capture.set(cv2.CAP_PROP_POS_FRAMES, round(time_s * fps))
                ok, frame = capture.read()
                if not ok:
                    raise RuntimeError(f"Frame decode failed: {name} {time_s}")
                frames.append(cv2.resize(frame, (640, 360), interpolation=cv2.INTER_AREA))
            transform = estimate_camera_transform(*frames)
            rows.append(
                {
                    "time_s": proposal["time_s"],
                    "shot_id": proposal["shot_id"],
                    "transform_found": transform is not None,
                    "tracked_features": transform["tracked_features"] if transform else 0,
                    "inliers": transform["inliers"] if transform else 0,
                    "inlier_fraction": round(transform["inlier_fraction"], 4) if transform else 0,
                    "registration_reliable": bool(transform and transform["reliable"]),
                }
            )
        capture.release()
        source_rows.append(
            {
                "source": name,
                "possible_edit_count": len(rows),
                "reliable_registration_count": sum(row["registration_reliable"] for row in rows),
                "rows": rows,
            }
        )
    output = {
        "status": "postscan_source_only_registration_diagnostic_not_cut_classifier",
        "sha256": {
            **hashes,
            "camera_motion_code": digest(ROOT / "prototype/camera_relative_motion.py"),
            "runner": digest(__file__),
        },
        "pair_spacing_s": 0.2,
        "sources": source_rows,
        "limitations": [
            "Registration failure can result from a real edit, a moving foreground subject, or occlusion.",
            "The existing reliability threshold was designed for stone motion, not trained as a cut classifier.",
            "These frame pairs were selected by the earlier possible-edit threshold and have no independent cut labels.",
        ],
    }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n")
    print(
        [
            (row["source"], row["possible_edit_count"], row["reliable_registration_count"])
            for row in source_rows
        ]
    )


if __name__ == "__main__":
    main()
