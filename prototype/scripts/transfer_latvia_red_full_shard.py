"""Frozen red-body/red-handle scan over a bounded earlier Latvia source shard.

This scans all source seconds, including time outside model candidate windows.
It records image proposals only; no physical throw labels are inferred.
"""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype/scripts"))
from probe_latvia_1080p_body_paths import matches
from screen_latvia_body_with_handle import handle_evidence

BASE = ROOT / "validation/throw-event-benchmark"
VIDEO = BASE / "canada-latvia-2024/source-1080p-1650-2760.mp4"
RED_AUDIT = BASE / "layout-router/full-2024-coverage/latvia24-full-v1/early-highres-red-template-selected-development.json"
OUT = BASE / "layout-router/full-2024-coverage/latvia24-full-v1"
CLIP_START_S, CLIP_STOP_S = 1650, 2760


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", required=True, type=int)
    parser.add_argument("--stop", required=True, type=int)
    args = parser.parse_args()
    if not CLIP_START_S <= args.start < args.stop <= CLIP_STOP_S or args.stop-args.start > 75:
        parser.error("Shard must be inside source and at most 75 seconds")
    out = OUT / f"early-highres-red-full-shard-{args.start}-{args.stop}.json"
    if out.exists():
        parser.error("Output exists; preserve first red full scan")
    audit = json.loads(RED_AUDIT.read_text())
    source_hash = digest(VIDEO)
    if audit["video_sha256"] != source_hash:
        raise ValueError("Video differs from red-template audit")
    cap = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG,
                           [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened() or cap.get(cv2.CAP_PROP_FPS) != 30:
        raise RuntimeError("Could not open expected 30-fps source")
    samples = []
    try:
        cap.set(cv2.CAP_PROP_POS_FRAMES,
                (audit["template_source_time_s"]-CLIP_START_S)*30)
        ok, frame = cap.read()
        if not ok:
            raise RuntimeError("Cannot decode red template source")
        x1, y1, x2, y2 = audit["template_xyxy_1080p"]
        template = cv2.resize(
            cv2.cvtColor(frame[y1:y2, x1:x2], cv2.COLOR_BGR2GRAY),
            (40, 19), interpolation=cv2.INTER_AREA)
        cap.set(cv2.CAP_PROP_POS_FRAMES, (args.start-CLIP_START_S)*30)
        for t in range(args.start, args.stop):
            ok, frame = cap.read()
            if not ok or frame.shape[:2] != (1080, 1920):
                raise RuntimeError(f"Cannot decode {t}")
            proposed = [{**p, **handle_evidence(frame, p)}
                        for p in matches(frame, template)]
            for point in proposed:
                point["red_handle_supported"] = bool(
                    point["handle_colour_pixels"]["red"] >= 120)
            if proposed:
                samples.append({"time_s": t, "body_proposals": proposed})
            if t+1 < args.stop:
                for _ in range(29):
                    if not cap.grab():
                        raise RuntimeError(f"Cannot advance from {t}")
    finally:
        cap.release()
    result = {
        "status": "full_excerpts_red_body_handle_shard_not_event_validation",
        "source_interval_s": [args.start, args.stop],
        "sample_period_s": 1,
        "source_video_sha256": source_hash,
        "red_template_audit_sha256": digest(RED_AUDIT),
        "runner_sha256": digest(Path(__file__)),
        "body_code_sha256": digest(
            ROOT / "prototype/scripts/probe_latvia_1080p_body_paths.py"),
        "handle_code_sha256": digest(
            ROOT / "prototype/scripts/screen_latvia_body_with_handle.py"),
        "body_proposal_count": sum(len(r["body_proposals"]) for r in samples),
        "red_handle_supported_count": sum(
            p["red_handle_supported"] for r in samples for p in r["body_proposals"]),
        "samples_with_body_proposals": samples,
        "limitations": [
            "Red template was selected after reviewing red misses in this same recording.",
            "A supported red-body image box is not a released stone or a physical board state.",
            "One-second sampling can miss a short visible segment or switch identities.",
        ],
    }
    out.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"interval": result["source_interval_s"],
                      "body": result["body_proposal_count"],
                      "red_handle": result["red_handle_supported_count"]}))


if __name__ == "__main__":
    main()
