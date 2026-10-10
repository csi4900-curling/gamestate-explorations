"""Run the frozen red-body/red-handle cue around one Latvia left candidate.

This is a prediction-targeted development transfer, not an event benchmark.
"""

import argparse
from hashlib import sha256
import json
from math import ceil
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype/scripts"))
from probe_latvia_1080p_body_paths import link_paths, matches
from screen_latvia_body_with_handle import handle_evidence

BASE = ROOT / "validation/throw-event-benchmark"
VIDEO = BASE / "canada-latvia-2024/source-1080p-1650-2760.mp4"
LEDGER = (
    BASE
    / "layout-router/full-2024-coverage/latvia24-full-v1/full-candidate-display-context-development.json"
)
RED_AUDIT = (
    BASE
    / "layout-router/full-2024-coverage/latvia24-full-v1/early-highres-red-template-selected-development.json"
)
OUT = BASE / "layout-router/full-2024-coverage/latvia24-full-v1"
CLIP_START_S = 1650


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--candidate-suffix", required=True, help="For example S49 for left:R01-S49"
    )
    args = parser.parse_args()
    if not args.candidate_suffix.startswith("S") or not args.candidate_suffix[1:].isdigit():
        parser.error("Expected candidate suffix such as S49")
    out = OUT / f"early-highres-red-window-{args.candidate_suffix}.json"
    if out.exists():
        parser.error("Output exists; preserve first window transfer")
    ledger = json.loads(LEDGER.read_text())
    audit = json.loads(RED_AUDIT.read_text())
    source_hash = digest(VIDEO)
    if audit["video_sha256"] != source_hash:
        raise ValueError("Source video differs from selected red audit")
    candidate_id = f"left:R01-{args.candidate_suffix}"
    rows = [r for r in ledger["candidates"] if r["candidate_id"] == candidate_id]
    if (
        len(rows) != 1
        or rows[0]["observation_kind"] != "left_provisional_passage"
        or rows[0]["colour_claim"] != "red"
    ):
        parser.error("Expected one provisional red candidate")
    candidate = rows[0]
    start = ceil(candidate["crossing_time_s"])
    stop = min(start + 26, 2760)
    cap = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened() or cap.get(cv2.CAP_PROP_FPS) != 30:
        raise RuntimeError("Could not open expected 30-fps source")
    samples = []
    try:
        cap.set(cv2.CAP_PROP_POS_FRAMES, (audit["template_source_time_s"] - CLIP_START_S) * 30)
        ok, frame = cap.read()
        if not ok:
            raise RuntimeError("Cannot decode red template frame")
        x1, y1, x2, y2 = audit["template_xyxy_1080p"]
        template = cv2.resize(
            cv2.cvtColor(frame[y1:y2, x1:x2], cv2.COLOR_BGR2GRAY),
            (40, 19),
            interpolation=cv2.INTER_AREA,
        )
        cap.set(cv2.CAP_PROP_POS_FRAMES, (start - CLIP_START_S) * 30)
        for t in range(start, stop):
            ok, frame = cap.read()
            if not ok or frame.shape[:2] != (1080, 1920):
                raise RuntimeError(f"Cannot decode {t}")
            proposed = [{**p, **handle_evidence(frame, p)} for p in matches(frame, template)]
            for p in proposed:
                p["red_handle_supported"] = bool(p["handle_colour_pixels"]["red"] >= 120)
            samples.append({"time_s": t, "body_proposals": proposed})
            if t + 1 < stop:
                for _ in range(29):
                    if not cap.grab():
                        raise RuntimeError(f"Could not advance from {t}")
    finally:
        cap.release()
    screened = [
        {
            "time_s": r["time_s"],
            "body_proposals": [p for p in r["body_proposals"] if p["red_handle_supported"]],
        }
        for r in samples
    ]
    paths = link_paths(screened)
    result = {
        "status": "prediction_targeted_red_body_handle_development_not_event_validation",
        "candidate_id": candidate_id,
        "candidate_crossing_time_s": candidate["crossing_time_s"],
        "source_interval_s": [start, stop],
        "source_video_sha256": source_hash,
        "candidate_ledger_sha256": digest(LEDGER),
        "red_template_audit_sha256": digest(RED_AUDIT),
        "runner_sha256": digest(Path(__file__)),
        "body_code_sha256": digest(ROOT / "prototype/scripts/probe_latvia_1080p_body_paths.py"),
        "handle_code_sha256": digest(ROOT / "prototype/scripts/screen_latvia_body_with_handle.py"),
        "body_proposal_count": sum(len(r["body_proposals"]) for r in samples),
        "red_handle_supported_count": sum(len(r["body_proposals"]) for r in screened),
        "samples_with_body_proposals": [r for r in samples if r["body_proposals"]],
        "supported_image_paths": paths,
        "upward_path_count": sum(p["direction"] == "upward" for p in paths),
        "limitations": [
            "Candidate times come from the provisional left detector, not independent labels.",
            "Red template and handle threshold were selected after reviewing two red moving examples.",
            "A path can be a parked or handled stone or a different physical event.",
            "This 26-second window cannot measure full-match false positives or throw recall.",
        ],
    }
    out.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                "candidate_id": candidate_id,
                "body": result["body_proposal_count"],
                "red_handle": result["red_handle_supported_count"],
                "upward_paths": result["upward_path_count"],
            }
        )
    )


if __name__ == "__main__":
    main()
