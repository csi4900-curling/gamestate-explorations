"""Replay every Latvia withheld raw crossing and capture crossing-local crops."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype/scripts"))
from build_2024_crossing_patch_packet import crossing_points  # noqa: E402
from build_2024_identity_patch_packet import crop_at, replay_track  # noqa: E402


BASE = ROOT / "validation/throw-event-benchmark/canada-latvia-2024"
VIDEO = BASE / "source-360p.mp4"
RAW = ROOT / "validation/throw-event-benchmark/layout-router/full-2024-coverage/latvia24-full-v1/run-02/events.json"
UNION = BASE / "full-match-area-censored-candidate-handoff-all-accepted-left-source-reviewed-development.json"
OUT = BASE / "withheld-left-crossing-patch-packet"


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def observed_crossing_samples(points, crossing_time_s):
    try:
        return crossing_points(points, crossing_time_s), "crossing_minus_0.2_zero_plus_0.2_s"
    except ValueError:
        nearest = sorted(points, key=lambda point: (
            abs(point["time_s"] - crossing_time_s), point["time_s"]))[:3]
        if len(nearest) < 3:
            raise ValueError("Fewer than three observed points near withheld crossing")
        return sorted(nearest, key=lambda point: point["time_s"]), "nearest_three_observed_points_fallback"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Withheld patch packet already exists")
    raw = json.loads(RAW.read_text())
    union = json.loads(UNION.read_text())
    if not (digest(VIDEO) == raw["source_sha256"] == union["source_sha256"]):
        raise ValueError("Withheld raw, full-match union, and video sources differ")
    source_classes = {row["candidate_id"]: row["source_pixel_review"] for row in
                      union["ordered_candidates"] if row["observation_kind"] ==
                      "left_unconfirmed_raw_motion"}
    if len(source_classes) != len(raw["withheld_events"]) or len(source_classes) != 47:
        raise ValueError("Withheld inventory differs")
    capture = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG,
                               [cv2.CAP_PROP_N_THREADS, 1])
    fps = capture.get(cv2.CAP_PROP_FPS)
    if not capture.isOpened() or fps <= 0:
        raise ValueError("Latvia source video is unreadable")
    args.output.mkdir(parents=True)
    rows = []
    try:
        for reference in raw["withheld_events"]:
            candidate_id = "left:R01-" + reference["id"]
            event, points = replay_track(capture, fps, reference)
            local, sampling_policy = observed_crossing_samples(
                points, event["crossing_time_s"])
            samples = []
            for index, point in enumerate(local, 1):
                relative = Path("crops") / f"R01-{reference['id']}-{index}.jpg"
                path = args.output / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                if not cv2.imwrite(str(path), crop_at(capture, fps, point),
                                   [cv2.IMWRITE_JPEG_QUALITY, 95]):
                    raise RuntimeError(f"Could not save {path}")
                samples.append({
                    "time_s": point["time_s"],
                    "pixel": point["pixel"],
                    "bbox": point["bbox"],
                    "body_support": point["body_support"],
                    "crop_path": str(relative),
                    "crop_sha256": digest(path),
                })
            previous_review = source_classes[candidate_id]
            if previous_review is None:
                source_review = "unreviewed"
            elif previous_review["source_pixel_class"].startswith("person"):
                source_review = "person_pixels"
            elif previous_review["source_pixel_class"].startswith("ambiguous"):
                source_review = "ambiguous_pixels"
            else:
                raise ValueError(f"Unknown previous withheld source class: {candidate_id}")
            rows.append({
                "source_id": union["source_id"],
                "event_id": "R01-" + reference["id"],
                "source_review": source_review,
                "review_kind": ("prior_same_agent_postproposal_review"
                                if previous_review is not None else "unreviewed_raw_candidate"),
                "timeline_crossing_time_s": reference["crossing_time_s"],
                "replayed_crossing_time_s": event["crossing_time_s"],
                "track_observations_at_confirmation": len(points),
                "sampling_policy": sampling_policy,
                "samples": samples,
            })
    finally:
        capture.release()
    result = {
        "status": "development_all_withheld_left_crossing_patch_packet_not_throw_truth",
        "source_id": union["source_id"],
        "source_video_sha256": digest(VIDEO),
        "raw_events_sha256": digest(RAW),
        "union_sha256": digest(UNION),
        "runner_sha256": digest(Path(__file__)),
        "replay_code_sha256": digest(ROOT / "prototype/scripts/build_2024_identity_patch_packet.py"),
        "crossing_sample_code_sha256": digest(ROOT / "prototype/scripts/build_2024_crossing_patch_packet.py"),
        "samples_per_event": 3,
        "rows": rows,
        "limitations": [
            "Withheld raw crossings are detector proposals, not verified throws.",
            "Prior source classes cover only selected rows and were assigned by the development agent.",
            "Three crossing-local crops do not verify physical delivery or same-stone continuity.",
            "Some short tracks use the nearest three observed points instead of the standard symmetric crossing sample; those scores are not directly comparable.",
        ],
    }
    (args.output / "manifest.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(f"Replayed {len(rows)} withheld left crossings")


if __name__ == "__main__":
    main()
