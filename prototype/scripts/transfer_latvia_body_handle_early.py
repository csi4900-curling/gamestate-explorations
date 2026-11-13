"""Frozen 1080p body+handle cue on a bounded Latvia source shard.

The candidate times are model proposals for association, not independent
throw truth. This transfer never changes the full-match event detector.
"""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype/scripts"))
from probe_latvia_1080p_body_paths import body_template, frame_at, matches
from screen_latvia_body_with_handle import handle_evidence

BASE = ROOT / "validation/throw-event-benchmark"
VIDEO = BASE / "canada-latvia-2024/source-1080p-1650-2760.mp4"
CANDIDATES = (
    BASE
    / "layout-router/full-2024-coverage/latvia24-full-v1/full-candidate-display-context-development.json"
)
BODY = (
    BASE
    / "layout-router/full-2024-coverage/latvia24-full-v1/end6-highres-body-template-development.json"
)
SCREEN = (
    BASE
    / "layout-router/full-2024-coverage/latvia24-full-v1/end6-highres-body-handle-screen-development.json"
)
START_S, STOP_S = 1650, 2760


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", type=int, required=True)
    parser.add_argument("--stop", type=int, required=True)
    args = parser.parse_args()
    if not START_S <= args.start < args.stop <= STOP_S or args.stop - args.start > 300:
        parser.error("Shard must be inside source interval and at most 300 s")
    out = (
        BASE
        / "layout-router/full-2024-coverage/latvia24-full-v1"
        / (f"early-highres-body-handle-shard-{args.start}-{args.stop}-sequential.json")
    )
    if out.exists():
        parser.error("Output exists; preserve first shard")
    body = json.loads(BODY.read_text())
    screen = json.loads(SCREEN.read_text())
    video_hash = digest(VIDEO)
    if body["positive_video_sha256"] != video_hash or screen["positive_video_sha256"] != video_hash:
        raise ValueError("1080p source differs from frozen probes")
    if screen["body_probe_sha256"] != digest(BODY):
        raise ValueError("Handle screen did not use frozen body probe")
    cap = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        raise RuntimeError("Cannot open 1080p video")
    samples = []
    try:
        template = body_template(frame_at(cap, 2310 - START_S))
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps != 30:
            raise ValueError("Sequential sampler expects this source at 30 fps")
        cap.set(cv2.CAP_PROP_POS_FRAMES, (args.start - START_S) * 30)
        for t in range(args.start, args.stop):
            ok, frame = cap.read()
            if not ok or frame.shape[:2] != (1080, 1920):
                raise RuntimeError(f"Could not decode {t} s")
            proposed = [
                {**point, **handle_evidence(frame, point)} for point in matches(frame, template)
            ]
            samples.append({"time_s": t, "body_proposals": proposed})
            if t + 1 < args.stop:
                for _ in range(29):
                    if not cap.grab():
                        raise RuntimeError(f"Could not advance from {t} s")
    finally:
        cap.release()
    result = {
        "status": "frozen_single_example_body_handle_transfer_shard_not_event_validation",
        "video_sha256": video_hash,
        "candidate_ledger_sha256": digest(CANDIDATES),
        "body_probe_sha256": digest(BODY),
        "handle_screen_sha256": digest(SCREEN),
        "body_code_sha256": digest(ROOT / "prototype/scripts/probe_latvia_1080p_body_paths.py"),
        "handle_code_sha256": digest(ROOT / "prototype/scripts/screen_latvia_body_with_handle.py"),
        "runner_sha256": digest(Path(__file__)),
        "source_interval_s": [args.start, args.stop],
        "sample_period_s": 1,
        "candidate_association_window_after_crossing_s": [0, 25],
        "body_proposal_count": sum(len(r["body_proposals"]) for r in samples),
        "handle_supported_count": sum(
            p["handle_supported"] for r in samples for p in r["body_proposals"]
        ),
        "samples_with_body_proposals": [r for r in samples if r["body_proposals"]],
        "limitations": [
            "Template was selected from the moving yellow stone at 2310 s in this same excerpt.",
            "Only other candidate windows test transfer beyond the chosen example; all model candidate times are unverified.",
            "An associated image path can be another moving object or a different stone.",
            "Absence of a path can reflect occlusion, view change, missed template match or wrong timing.",
            "No independent throw precision, recall or cross-recording validation is implied.",
        ],
    }
    out.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                "body_proposals": result["body_proposal_count"],
                "handle_supported": result["handle_supported_count"],
                "interval": result["source_interval_s"],
            }
        )
    )


if __name__ == "__main__":
    main()
