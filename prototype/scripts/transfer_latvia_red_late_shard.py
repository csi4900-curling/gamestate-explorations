"""Transfer frozen red-body/red-handle cue to Latvia's late blind interval.

This scans all right-view source seconds, not prediction-selected windows.
Outputs are image proposals; no physical delivery is inferred.
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
TEMPLATE_VIDEO = BASE / "canada-latvia-2024/source-1080p-1650-2760.mp4"
VIDEO = BASE / "canada-latvia-2024/source-1080p-5670-6670.mp4"
RED_AUDIT = (
    BASE
    / "layout-router/full-2024-coverage/latvia24-full-v1/early-highres-red-template-selected-development.json"
)
OUT = BASE / "layout-router/full-2024-coverage/latvia24-full-v1"
CLIP_START_S, CLIP_STOP_S = 5670, 6670


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
    if not CLIP_START_S <= args.start < args.stop <= CLIP_STOP_S or args.stop - args.start > 75:
        parser.error("Shard must be inside source and at most 75 seconds")
    out = OUT / f"end6-highres-red-full-shard-{args.start}-{args.stop}.json"
    if out.exists():
        parser.error("Output exists; preserve first late red transfer")
    audit = json.loads(RED_AUDIT.read_text())
    template_hash = digest(TEMPLATE_VIDEO)
    video_hash = digest(VIDEO)
    if audit["video_sha256"] != template_hash:
        raise ValueError("Template source differs from red audit")
    source = cv2.VideoCapture(str(TEMPLATE_VIDEO), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    target = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if (
        not source.isOpened()
        or not target.isOpened()
        or source.get(cv2.CAP_PROP_FPS) != 30
        or target.get(cv2.CAP_PROP_FPS) != 30
    ):
        raise RuntimeError("Could not open expected 30-fps sources")
    samples = []
    try:
        source.set(cv2.CAP_PROP_POS_FRAMES, (audit["template_source_time_s"] - 1650) * 30)
        ok, frame = source.read()
        if not ok:
            raise RuntimeError("Cannot decode red template source")
        x1, y1, x2, y2 = audit["template_xyxy_1080p"]
        template = cv2.resize(
            cv2.cvtColor(frame[y1:y2, x1:x2], cv2.COLOR_BGR2GRAY),
            (40, 19),
            interpolation=cv2.INTER_AREA,
        )
        target.set(cv2.CAP_PROP_POS_FRAMES, (args.start - CLIP_START_S) * 30)
        for t in range(args.start, args.stop):
            ok, frame = target.read()
            if not ok or frame.shape[:2] != (1080, 1920):
                raise RuntimeError(f"Cannot decode {t}")
            proposed = [{**p, **handle_evidence(frame, p)} for p in matches(frame, template)]
            for point in proposed:
                point["red_handle_supported"] = bool(point["handle_colour_pixels"]["red"] >= 120)
            if proposed:
                samples.append({"time_s": t, "body_proposals": proposed})
            if t + 1 < args.stop:
                for _ in range(29):
                    if not target.grab():
                        raise RuntimeError(f"Cannot advance from {t}")
    finally:
        source.release()
        target.release()
    result = {
        "status": "late_blind_red_body_handle_shard_not_event_validation",
        "source_interval_s": [args.start, args.stop],
        "sample_period_s": 1,
        "source_video_sha256": video_hash,
        "template_video_sha256": template_hash,
        "red_template_audit_sha256": digest(RED_AUDIT),
        "runner_sha256": digest(Path(__file__)),
        "body_code_sha256": digest(ROOT / "prototype/scripts/probe_latvia_1080p_body_paths.py"),
        "handle_code_sha256": digest(ROOT / "prototype/scripts/screen_latvia_body_with_handle.py"),
        "body_proposal_count": sum(len(r["body_proposals"]) for r in samples),
        "red_handle_supported_count": sum(
            p["red_handle_supported"] for r in samples for p in r["body_proposals"]
        ),
        "samples_with_body_proposals": samples,
        "limitations": [
            "Colour-specific body template was selected within this same match, earlier in time.",
            "Parked or handled stones and player/equipment textures may pass the image screen.",
            "One-second observations and nearest links cannot establish event recall or stone identity.",
        ],
    }
    out.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                "interval": result["source_interval_s"],
                "body": result["body_proposal_count"],
                "red_handle": result["red_handle_supported_count"],
            }
        )
    )


if __name__ == "__main__":
    main()
