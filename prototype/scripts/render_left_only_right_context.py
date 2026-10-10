"""Show right-camera frames around left events with no right temporal candidate."""

import argparse
from hashlib import sha256
import json
from pathlib import Path

import cv2
import numpy as np


def digest(path):
    result = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("video", "timeline", "inventory", "output_dir"):
        parser.add_argument(f"--{name.replace('_', '-')}", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error("Output directory already exists")
    timeline = json.loads(args.timeline.read_text())
    inventory = json.loads(args.inventory.read_text())
    if (digest(args.video) != timeline["source_sha256"]
            or inventory["source_sha256"] != timeline["source_sha256"]
            or inventory["timeline_sha256"] != digest(args.timeline)):
        parser.error("Source, timeline and inventory differ")
    ids = inventory["left_events_without_any_right_time_colour_candidate"]
    events = {row["id"]: row for row in timeline["observed_events"]}
    if len(events) != len(timeline["observed_events"]) or any(id not in events for id in ids):
        parser.error("Left ID coverage differs")
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG,
                           [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        parser.error("Cannot open source video")
    fps = cap.get(cv2.CAP_PROP_FPS)
    rows, sheets = [], []
    args.output_dir.mkdir(parents=True)
    try:
        for start in range(0, len(ids), 3):
            group = ids[start:start + 3]
            sheet = np.full((380 * len(group), 1600, 3), 20, dtype=np.uint8)
            name = f"sheet-{start // 3 + 1:02}.jpg"
            for i, event_id in enumerate(group):
                t = events[event_id]["crossing_time_s"]
                samples = []
                for col, offset in enumerate((-12, -6, 0, 6, 12)):
                    source_t = t + offset
                    index = round(source_t * fps)
                    cap.set(cv2.CAP_PROP_POS_FRAMES, index)
                    ok, frame = cap.read()
                    if not ok:
                        raise RuntimeError(f"Could not decode {source_t:.3f} s")
                    frame = cv2.resize(frame, (640, 360),
                                       interpolation=cv2.INTER_AREA)
                    right = frame[:, 320:640]
                    top, x = i * 380, col * 320
                    sheet[top + 20:top + 380, x:x + 320] = right
                    cv2.putText(sheet, f"{event_id} {source_t:.1f}s",
                                (x + 5, top + 16), cv2.FONT_HERSHEY_SIMPLEX,
                                .43, (255, 255, 255), 1)
                    samples.append({"source_time_s": round(source_t, 3),
                                    "decoded_frame_index": index})
                rows.append({"left_event_id": event_id,
                             "left_colour_claim": events[event_id]["colour"],
                             "left_crossing_time_s": t,
                             "sheet": name, "samples": samples})
            path = args.output_dir / name
            if not cv2.imwrite(str(path), sheet):
                raise RuntimeError(f"Could not write {path}")
            sheets.append({"file": name, "sha256": digest(path),
                           "left_event_ids": group})
    finally:
        cap.release()
    result = {
        "status": "right_context_for_left_only_events_not_negative_source_truth",
        "source_sha256": timeline["source_sha256"],
        "timeline_sha256": digest(args.timeline),
        "inventory_sha256": digest(args.inventory),
        "runner_sha256": digest(Path(__file__)),
        "rows": rows, "sheets": sheets,
        "limitations": [
            "Six-second sample spacing can miss a short right-camera stone path.",
            "No right proposal does not mean the throw was not visible or did not occur.",
        ],
    }
    (args.output_dir / "manifest.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"left_only_events": len(rows), "sheets": len(sheets)}))


if __name__ == "__main__":
    main()
