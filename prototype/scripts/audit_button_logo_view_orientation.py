"""Source-only button-emblem orientation across selected camera handoffs."""

from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.button_logo_orientation import (logo_colour_signature,
                                               relative_view_rotation)

BASE = ROOT / "validation/official-shot-sequence"
OUTPUT = BASE / "button-logo-cross-view-orientation-development.json"
CASES = [
    {
        "name": "china_end2_s12",
        "video": ROOT / "validation/throw-event-benchmark/paralympics-2022-canada-china/source.mp4",
        "overhead": BASE / "china-end2-adjacent-video-boards-first.json",
        "overhead_shot_id": "PREL000102-E02-S12",
        "wide": BASE / "china-end2-wide-perspective-cap-evidence-development.json",
        "wide_shot_id": None,
    },
    {
        "name": "swiss_end2_s13",
        "video": ROOT / "validation/throw-event-benchmark/paralympics-2022-sweden-switzerland/source.mp4",
        "overhead": BASE / "swiss-end2-adjacent-video-boards-first.json",
        "overhead_shot_id": "PREL000101-E02-S13",
        "wide": BASE / "swiss-end2-wide-blue-ring-v2-development.json",
        "wide_shot_id": "PREL000101-E02-S13",
    },
]


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def signature_frames(capture, fps, observations, *, view):
    rows = []
    for observation in observations:
        time_s = observation["time_s"]
        capture.set(cv2.CAP_PROP_POS_FRAMES, round(time_s * fps))
        ok, frame = capture.read()
        if not ok:
            raise RuntimeError(f"Cannot decode {time_s} s")
        frame = cv2.resize(frame, (640, 360))
        if view == "overhead":
            house = observation["house"]
            center = house["center_px"]
            axes = [house["outer_radius_px"]] * 2
        else:
            ellipse = observation["ellipse"]
            center = ellipse["center_px"]
            axes = [max(ellipse["axis_lengths_px"]) / 2,
                    min(ellipse["axis_lengths_px"]) / 2]
        rows.append({"time_s": time_s, "center_px": center,
                     "outer_axes_px": axes,
                     "signature": logo_colour_signature(frame, center, axes)})
    return rows


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first logo-orientation audit")
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    cases = []
    for config in CASES:
        source_hash = digest(config["video"])
        if source_hash == reserved["source_sha256"]:
            raise ValueError("Reserved source selected")
        overhead_artifact = json.loads(config["overhead"].read_text())
        wide_artifact = json.loads(config["wide"].read_text())
        if (source_hash != overhead_artifact["source_sha256"]
                or source_hash != wide_artifact["source_sha256"]):
            raise ValueError("Source fingerprint mismatch")
        overhead = next(row["frame_observations"] for row in overhead_artifact["rows"]
                        if row["shot_id"] == config["overhead_shot_id"])
        if config["wide_shot_id"] is None:
            wide = wide_artifact["frames"]
        else:
            wide = next(row["wide_frames"] for row in wide_artifact["rows"]
                        if row["shot_id"] == config["wide_shot_id"])
        capture = cv2.VideoCapture(str(config["video"]), cv2.CAP_FFMPEG,
                                   [cv2.CAP_PROP_N_THREADS, 1])
        fps = capture.get(cv2.CAP_PROP_FPS)
        overhead_signatures = signature_frames(capture, fps, overhead, view="overhead")
        wide_signatures = signature_frames(capture, fps, wide, view="wide")
        capture.release()
        pairs = [{"overhead_time_s": left["time_s"],
                  "wide_time_s": right["time_s"],
                  "relative_rotation_degrees": relative_view_rotation(
                      left["signature"], right["signature"])}
                 for left in overhead_signatures for right in wide_signatures]
        resolved = {row["relative_rotation_degrees"] for row in pairs
                    if row["relative_rotation_degrees"] is not None}
        cases.append({
            "name": config["name"],
            "source_sha256": source_hash,
            "overhead_artifact_sha256": digest(config["overhead"]),
            "wide_artifact_sha256": digest(config["wide"]),
            "overhead_frames": overhead_signatures,
            "wide_frames": wide_signatures,
            "cross_view_pairs": pairs,
            "resolved_pair_count": sum(row["relative_rotation_degrees"] is not None
                                       for row in pairs),
            "unanimous_relative_rotation_degrees": next(iter(resolved))
            if len(resolved) == 1 and all(row["relative_rotation_degrees"] is not None
                                          for row in pairs) else None,
        })
    output = {
        "status": "selected_source_only_button_logo_orientation_development",
        "logo_code_sha256": digest(ROOT / "prototype/button_logo_orientation.py"),
        "runner_sha256": digest(Path(__file__)),
        "cases": cases,
        "limitations": [
            "Both handoffs were selected after earlier board failures and are development data.",
            "The cue is specific to the asymmetric Beijing 2022 Paralympic rink emblem.",
            "Logo pixels can be occluded by stones, players or implements; unresolved frames must abstain.",
            "This determines relative image rotation, not metric perspective calibration or physical stone identity.",
            "No official diagram positions or reserved source are used.",
        ],
    }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n")
    print([(row["name"], row["resolved_pair_count"],
            len(row["cross_view_pairs"]), row["unanimous_relative_rotation_degrees"])
           for row in cases])


if __name__ == "__main__":
    main()
