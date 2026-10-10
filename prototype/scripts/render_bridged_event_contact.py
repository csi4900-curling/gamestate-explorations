"""Show source frames around bridged-run events absent from a prior timeline."""

import argparse
from hashlib import sha256
import json
from pathlib import Path

import cv2
import numpy as np


def digest(path):
    h = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", required=True, type=Path)
    parser.add_argument("--timeline", required=True, type=Path)
    parser.add_argument("--baseline-timeline", type=Path)
    parser.add_argument("--event-id", action="append", default=[],
                        help="Limit source review to these timeline event IDs")
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error("Output directory exists; preserve original review")
    timeline = json.loads(args.timeline.read_text())
    if digest(args.video) != timeline["source_sha256"]:
        parser.error("Video differs from timeline")
    baseline = []
    if args.baseline_timeline:
        old = json.loads(args.baseline_timeline.read_text())
        if old["source_sha256"] != timeline["source_sha256"]:
            parser.error("Baseline source differs")
        baseline = old["observed_events"]
    observations = timeline.get("observed_events", timeline.get("events"))
    if observations is None:
        parser.error("Input has no observed_events or events list")
    events = [event for event in observations if not any(
        prior["colour"] == event["colour"] and
        abs(prior["crossing_time_s"] - event["crossing_time_s"]) <= 0.25
        for prior in baseline)]
    if args.event_id:
        wanted = set(args.event_id)
        events = [event for event in events if event["id"] in wanted]
        if {event["id"] for event in events} != wanted:
            parser.error("At least one requested event ID is absent")
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG,
                           [cv2.CAP_PROP_N_THREADS, 1])
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        raise RuntimeError("Unreadable video")
    args.output_dir.mkdir(parents=True)
    sheets = []
    for sheet_index in range(0, len(events), 5):
        group = events[sheet_index:sheet_index + 5]
        sheet = np.full((len(group) * 390, 1920, 3), 25, dtype=np.uint8)
        for row_index, event in enumerate(group):
            t = event["crossing_time_s"]
            for col, offset in enumerate((-1.0, 0.0, 1.0)):
                seconds = t + offset
                cap.set(cv2.CAP_PROP_POS_FRAMES, round(seconds * fps))
                ok, frame = cap.read()
                if not ok:
                    raise RuntimeError(f"Cannot decode {seconds:.3f}")
                image = cv2.resize(frame, (640, 360), interpolation=cv2.INTER_AREA)
                y, x = row_index * 390, col * 640
                sheet[y + 30:y + 390, x:x + 640] = image
                cv2.putText(sheet, f"{event['id']} {event['colour']} {seconds:.2f}s",
                            (x + 8, y + 21), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                            (255, 255, 255), 1, cv2.LINE_AA)
        path = args.output_dir / f"sheet-{sheet_index // 5 + 1:02d}.jpg"
        if not cv2.imwrite(str(path), sheet):
            raise RuntimeError("Could not write sheet")
        sheets.append({"path": path.name, "sha256": digest(path),
                       "event_ids": [row["id"] for row in group]})
    cap.release()
    manifest = {
        "status": "prediction_targeted_source_review_not_independent_labels",
        "source_sha256": timeline["source_sha256"],
        "timeline_sha256": digest(args.timeline),
        "baseline_timeline_sha256": digest(args.baseline_timeline)
        if args.baseline_timeline else None,
        "event_count": len(events),
        "events": [{"id": row["id"], "time_s": row["crossing_time_s"],
                    "colour": row["colour"]} for row in events],
        "sheets": sheets,
        "limitations": [
            "Three stills per prediction cannot verify physical delivery identity.",
            "Events were selected from model predictions; this is not independent scoring.",
        ],
    }
    (args.output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"review_events": len(events), "sheets": len(sheets)}))


if __name__ == "__main__":
    main()
