"""Compare frozen and revised box models in exposed Norway end-2 shot windows.

This is a targeted development diagnostic selected using the prior counter
alignment. It cannot score physical throws or independently validate identity.
"""

from collections import Counter
from hashlib import sha256
import json
from math import ceil
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from scripts.audit_full_shot_cap_motion import tracks_for_shot
from stone_patch_detector import detect_stones, load_model

BASE = ROOT / "validation/throw-event-benchmark/paralympics-2022-canada-norway"
VIDEO = BASE / "source.mp4"
FIRST = BASE / "FIRST-TRANSFER.json"
SHOTS = (
    ROOT
    / "validation/curlobserver-learned-probe/canada-norway-full-transfer/selected-learned-motion.json"
)
OLD = ROOT / "validation/curlobserver-learned-probe/model-v1/model.npz"
NEW = ROOT / "validation/curlobserver-learned-probe/public-tracking-v2/model.npz"
OUTPUT = (
    ROOT
    / "validation/curlobserver-learned-probe/public-tracking-v2/norway-end2-targeted-transfer.json"
)

# Four known counter-colour conflicts and four agreement controls. Selection
# deliberately uses the exposed first transfer; it is not a held-out test.
IDS = ("S93", "S95", "S97", "S99", "S115", "S129", "S139", "S156")


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first targeted model-swap audit")
    first = json.loads(FIRST.read_text())
    source_hash = digest(VIDEO)
    if first["source_video_sha256"] != source_hash:
        raise ValueError("Frozen first transfer has another source")
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    if source_hash == reserved["source_sha256"]:
        raise ValueError("Reserved independent source is not development data")
    shots = json.loads(SHOTS.read_text())
    if shots["source_sha256"] != source_hash:
        raise ValueError("Shot windows have another source")
    by_id = {row["shot_id"]: row for row in shots["shots"]}
    score = first["complete_counter_anchored_ends"][0]["cap_only_score"]
    by_match = {row["visual_id"]: row for row in score["matches"]}
    if not all(key in by_match and key in by_id for key in IDS):
        raise ValueError("Declared frozen end-2 controls changed")
    models = {"frozen_v1": load_model(OLD), "public_clip_v2": load_model(NEW)}
    capture = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not capture.isOpened():
        raise ValueError("Cannot open source")
    fps = capture.get(cv2.CAP_PROP_FPS)
    step = round(fps / 5)
    if fps <= 0 or step < 1:
        raise ValueError("Invalid video rate")
    rows = []
    for shot_id in IDS:
        interval = by_id[shot_id]["interval_s"]
        first_frame, last_frame = ceil(interval[0] * fps), ceil(interval[1] * fps)
        capture.set(cv2.CAP_PROP_POS_FRAMES, first_frame)
        observations = {model: {"red": {}, "yellow": {}} for model in models}
        counts = {model: Counter() for model in models}
        frame_rows = []
        for frame_index in range(first_frame, last_frame):
            if not capture.grab():
                raise RuntimeError(f"Decode failed at frame {frame_index}")
            if frame_index % step:
                continue
            ok, frame = capture.retrieve()
            if not ok:
                raise RuntimeError(f"Retrieve failed at frame {frame_index}")
            t = round(frame_index / fps, 3)
            per_model = {}
            for model_name, model in models.items():
                boxes = detect_stones(frame, model)
                per_model[model_name] = boxes
                for box in boxes:
                    x, y, width, height = box["bbox"]
                    observations[model_name][box["colour"]].setdefault(t, []).append(
                        {
                            "pixel": [x + width / 2, y + height / 2],
                            "bbox": box["bbox"],
                            "confidence": box["confidence"],
                        }
                    )
                    counts[model_name][box["colour"]] += 1
                counts[model_name]["frames"] += 1
            frame_rows.append({"time_s": t, "detections": per_model})
        model_rows = {}
        for model_name in models:
            sampled = {
                colour: sorted(observations[model_name][colour].items())
                for colour in ("red", "yellow")
            }
            tracks = tracks_for_shot(sampled, shot_id)
            model_rows[model_name] = {
                "frame_count": counts[model_name]["frames"],
                "box_counts": {colour: counts[model_name][colour] for colour in ("red", "yellow")},
                "supported_track_counts": dict(Counter(row["colour"] for row in tracks)),
                "supported_tracks": tracks,
            }
        match = by_match[shot_id]
        rows.append(
            {
                "shot_id": shot_id,
                "interval_s": interval,
                "frozen_visual_colour": match["visual_colour"],
                "counter_proxy_colour": match["counter_colour"],
                "counter_pair_official_shot_id": match["official_shot_id"],
                "model_evidence": model_rows,
                "sampled_frames": frame_rows,
            }
        )
    capture.release()
    output = {
        "status": "exposed_development_targeted_model_swap_not_event_score",
        "source_sha256": source_hash,
        "first_transfer_sha256": digest(FIRST),
        "shot_windows_sha256": digest(SHOTS),
        "model_sha256": {"frozen_v1": digest(OLD), "public_clip_v2": digest(NEW)},
        "detector_code_sha256": digest(ROOT / "prototype/stone_patch_detector.py"),
        "runner_sha256": digest(Path(__file__)),
        "sample_rate_hz": fps / step,
        "selection": "Four frozen end-2 known-colour conflicts and four colour-agreement controls, fixed before running this model swap.",
        "rows": rows,
        "limitations": [
            "Cases were chosen after inspecting the first full-match transfer.",
            "A counter colour is a proxy for the delivered stone and may be paired with the wrong visual interval.",
            "Box counts and within-window motion tracks are not true-stone labels, throw precision/recall, or cross-view identity.",
            "The public clip split may share production material with model training images.",
        ],
    }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n")
    for row in rows:
        print(
            row["shot_id"],
            row["counter_proxy_colour"],
            {name: data["supported_track_counts"] for name, data in row["model_evidence"].items()},
        )


if __name__ == "__main__":
    main()
