"""Measure underpoint image context on every Czech raw span proposal."""

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
VIDEO = BASE / "canada-czech-2024/source-1080p-full-format270.mp4"
RUN = BASE / "layout-router/czech24-full-camera-motion-v1/run-02"
RAW = RUN / "raw.json"
EVENTS = RUN / "events.json"
ALIGNMENT = BASE / "canada-czech-2024/lowres-split-registration-positive-and-board-controls-development.json"
OUT = RUN / "raw-underpoint-context-development.json"


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def main():
    if OUT.exists():
        raise ValueError("Raw underpoint audit exists")
    raw, events, alignment = (json.loads(p.read_text()) for p in
                              (RAW, EVENTS, ALIGNMENT))
    if (digest(VIDEO) != alignment["source_1080p_sha256"] or
            raw["source_sha256"] != alignment["source_video_sha256"] or
            events["source_sha256"] != raw["source_sha256"] or
            len(raw["events"]) != 147):
        raise ValueError("Source, alignment or proposal inventory differs")
    confirmed = {e["id"] for e in events["events"]}
    cap = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG,
                           [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        raise ValueError("High-resolution source unreadable")
    fps = cap.get(cv2.CAP_PROP_FPS)
    rows = []
    try:
        for event in raw["events"]:
            points = event["observed_track_points"]
            indices = sorted({round((len(points) - 1) * q)
                              for q in (0.2, 0.5, 0.8)})
            samples = []
            for index in indices:
                point = points[index]
                t = point["time_s"]
                cap.set(cv2.CAP_PROP_POS_FRAMES, round(t * fps))
                ok, frame = cap.read()
                if not ok:
                    raise ValueError(f"Frame unreadable at {t}")
                pixel = [3 * v for v in point["pixel"]]
                samples.append({
                    "source_time_s": t,
                    "video_frame_index": int(cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1,
                    "raw_center_1080p_px": pixel,
                    "underpoint_nonice_fraction": underpoint_nonice_fraction(
                        frame, pixel),
                })
            values = [s["underpoint_nonice_fraction"] for s in samples
                      if s["underpoint_nonice_fraction"] is not None]
            rows.append({
                "candidate_id": event["id"],
                "context_confirmed": event["id"] in confirmed,
                "sample_count": len(samples),
                "measured_count": len(values),
                "median_nonice_fraction": statistics.median(values)
                    if values else None,
                "samples": samples,
            })
    finally:
        cap.release()
    measured = [r["median_nonice_fraction"] for r in rows
                if r["median_nonice_fraction"] is not None]
    summary = {
        "raw_proposals": len(rows),
        "context_confirmed": len(confirmed),
        "measured_candidates": len(measured),
        "median_of_candidate_medians": statistics.median(measured),
        "candidate_sample_count_distribution": dict(Counter(
            r["sample_count"] for r in rows)),
        "selected_development_examples": {
            id: next(r["median_nonice_fraction"] for r in rows
                     if r["candidate_id"] == id)
            for id in ("S07", "S21", "S42", "S69", "S96", "S143")},
    }
    OUT.write_text(json.dumps({
        "status": "full_raw_underpoint_context_development_not_stone_truth",
        "source_360p_sha256": raw["source_sha256"],
        "source_1080p_sha256": alignment["source_1080p_sha256"],
        "source_time_offset_s": 0,
        "input_sha256": {"raw": digest(RAW), "events": digest(EVENTS),
                         "alignment": digest(ALIGNMENT)},
        "feature_code_sha256": digest(ROOT /
            "prototype/highres_underpoint_context.py"),
        "runner_sha256": digest(Path(__file__)),
        "sample_strategy": "20%, 50%, 80% of observed raw track before confirmation; 360p pixel centres scaled exactly 3x into aligned 1080p source; no threshold",
        "summary": summary,
        "rows": rows,
        "limitations": [
            "No physical stone identity or exhaustive throw reference is used here.",
            "The feature was designed on later receiving-view body paths; raw early cap centres are a different use and may be near players or rink markings.",
            "S96 has a same-agent review of its raw player/wheelchair-attached pixels. S143 and the selected source-visible S07, S21, S42 and S69 stone controls were reviewed on downstream associated paths; raw-to-downstream identity is unverified.",
        ],
    }, indent=2) + "\n")
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
