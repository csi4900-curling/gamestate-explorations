"""Apply the Czech raw-underpoint sampling rule unchanged to Latvia 2024."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import statistics
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from highres_underpoint_context import underpoint_nonice_fraction  # noqa: E402

BASE = ROOT / "validation/throw-event-benchmark"
LATVIA = BASE / "canada-latvia-2024"
VIDEO = LATVIA / "source-1080p-1650-2760.mp4"
FULL = LATVIA / "source-360p.mp4"
ALIGNMENT = LATVIA / "highres-alignment-frozen-first.json"
RUN = BASE / "layout-router/latvia24-1650-2760-raw-context-v1"
RAW, EVENTS = RUN / "raw.json", RUN / "events.json"
CZECH = (
    BASE
    / "layout-router/czech24-full-camera-motion-v1/run-02/raw-underpoint-context-development.json"
)
OUT = RUN / "raw-underpoint-context-development.json"


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def main():
    if OUT.exists():
        raise ValueError("Latvia raw-underpoint transfer exists")
    raw, events, alignment, czech = (
        json.loads(p.read_text()) for p in (RAW, EVENTS, ALIGNMENT, CZECH)
    )
    if (
        digest(FULL) != alignment["full_video_sha256"]
        or digest(VIDEO) != alignment["interval_video_sha256"]
        or raw["source_sha256"] != alignment["full_video_sha256"]
        or events["source_sha256"] != raw["source_sha256"]
        or raw["source_interval_s"] != [1650.0, 2760.0]
        or alignment["source_offset_s"] != 1650
        or czech["feature_code_sha256"] != digest(ROOT / "prototype/highres_underpoint_context.py")
    ):
        raise ValueError("Latvia source or unchanged Czech feature lineage differs")
    cap = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        raise ValueError("High-resolution source unreadable")
    fps = cap.get(cv2.CAP_PROP_FPS)
    confirmed = {e["id"] for e in events["events"]}
    rows = []
    try:
        for event in raw["events"]:
            points = event["observed_track_points"]
            indices = sorted({round((len(points) - 1) * q) for q in (0.2, 0.5, 0.8)})
            samples = []
            for index in indices:
                point = points[index]
                t = point["time_s"]
                cap.set(cv2.CAP_PROP_POS_FRAMES, round((t - alignment["source_offset_s"]) * fps))
                ok, frame = cap.read()
                if not ok:
                    raise ValueError(f"Frame unreadable at {t}")
                pixel = [3 * v for v in point["pixel"]]
                samples.append(
                    {
                        "source_time_s": t,
                        "video_frame_index": int(cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1,
                        "raw_center_1080p_px": pixel,
                        "underpoint_nonice_fraction": underpoint_nonice_fraction(frame, pixel),
                    }
                )
            values = [
                s["underpoint_nonice_fraction"]
                for s in samples
                if s["underpoint_nonice_fraction"] is not None
            ]
            rows.append(
                {
                    "candidate_id": event["id"],
                    "context_confirmed": event["id"] in confirmed,
                    "sample_count": len(samples),
                    "measured_count": len(values),
                    "median_nonice_fraction": statistics.median(values) if values else None,
                    "samples": samples,
                }
            )
    finally:
        cap.release()
    if len(rows) != len(raw["events"]) or len({r["candidate_id"] for r in rows}) != len(rows):
        raise ValueError("Raw candidate coverage differs")
    measured = [
        r["median_nonice_fraction"] for r in rows if r["median_nonice_fraction"] is not None
    ]
    tier = lambda value: (
        "clear" if value <= 0.05 else ("cluttered" if value > 0.25 else "ambiguous")
    )
    summary = {
        "raw_proposals": len(rows),
        "context_confirmed": len(confirmed),
        "measured_candidates": len(measured),
        "median_of_candidate_medians": statistics.median(measured),
        "descriptive_tier_counts": dict(Counter(tier(value) for value in measured)),
    }
    OUT.write_text(
        json.dumps(
            {
                "status": "unchanged_czech_raw_underpoint_rule_latvia_development_transfer_not_throw_truth",
                "source_360p_sha256": raw["source_sha256"],
                "source_1080p_sha256": alignment["interval_video_sha256"],
                "source_time_offset_s": alignment["source_offset_s"],
                "input_sha256": {
                    "raw": digest(RAW),
                    "events": digest(EVENTS),
                    "alignment": digest(ALIGNMENT),
                    "czech_audit": digest(CZECH),
                },
                "feature_code_sha256": digest(ROOT / "prototype/highres_underpoint_context.py"),
                "runner_sha256": digest(Path(__file__)),
                "sample_strategy": czech["sample_strategy"],
                "summary": summary,
                "rows": rows,
                "limitations": [
                    "The 2024 source family and selected interval were already used in development; this is not independent event validation.",
                    "Descriptive tiers came from later receiving-view paths and are not raw-trigger rejection rules.",
                    "No complete physical throw reference or stone identity is established.",
                ],
            },
            indent=2,
        )
        + "\n"
    )
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
