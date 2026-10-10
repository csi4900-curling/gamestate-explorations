"""Render source frames for left events without any right time/colour candidate."""

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
    if (
        timeline["source_sha256"] != inventory["source_sha256"]
        or timeline["source_sha256"] != digest(args.video)
        or inventory["timeline_sha256"] != digest(args.timeline)
    ):
        parser.error("Source and inventory lineage differs")
    ids = inventory["left_events_without_any_right_time_colour_candidate"]
    events = {row["id"]: row for row in timeline["observed_events"]}
    if len(events) != len(timeline["observed_events"]) or any(id not in events for id in ids):
        parser.error("Left event IDs differ")
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        parser.error("Could not open source video")
    fps = cap.get(cv2.CAP_PROP_FPS)
    rows, sheets = [], []
    args.output_dir.mkdir(parents=True)
    try:
        for start in range(0, len(ids), 5):
            group = ids[start : start + 5]
            sheet = np.full((380 * len(group), 960, 3), 20, dtype=np.uint8)
            name = f"sheet-{start // 5 + 1:02}.jpg"
            for i, event_id in enumerate(group):
                event = events[event_id]
                t = event["crossing_time_s"]
                samples = []
                for col, source_t in enumerate((t - 1, t, t + 1)):
                    index = round(source_t * fps)
                    cap.set(cv2.CAP_PROP_POS_FRAMES, index)
                    ok, frame = cap.read()
                    if not ok:
                        raise RuntimeError(f"Could not decode {source_t:.3f} s")
                    frame = cv2.resize(frame, (640, 360), interpolation=cv2.INTER_AREA)
                    crop = frame[:, :320].copy()
                    if col == 1:
                        cv2.circle(
                            crop,
                            (round(event["crossing_x_px"]), round(event["passage_y_px"])),
                            9,
                            (0, 255, 0),
                            2,
                        )
                    top, left = i * 380, col * 320
                    sheet[top + 20 : top + 380, left : left + 320] = crop
                    cv2.putText(
                        sheet,
                        f"{event_id} {source_t:.1f}s",
                        (left + 5, top + 16),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.45,
                        (255, 255, 255),
                        1,
                    )
                    samples.append(
                        {"source_time_s": round(source_t, 3), "decoded_frame_index": index}
                    )
                rows.append(
                    {
                        "left_event_id": event_id,
                        "colour_claim": event["colour"],
                        "crossing_time_s": t,
                        "crossing_pixel_left_640x360": [
                            event["crossing_x_px"],
                            event["passage_y_px"],
                        ],
                        "sheet": name,
                        "samples": samples,
                    }
                )
            path = args.output_dir / name
            if not cv2.imwrite(str(path), sheet):
                raise RuntimeError(f"Could not write {path}")
            sheets.append({"file": name, "sha256": digest(path), "left_event_ids": group})
    finally:
        cap.release()
    payload = {
        "status": "left_only_event_source_stills_not_delivery_labels",
        "source_sha256": timeline["source_sha256"],
        "timeline_sha256": digest(args.timeline),
        "inventory_sha256": digest(args.inventory),
        "runner_sha256": digest(Path(__file__)),
        "rows": rows,
        "sheets": sheets,
        "limitations": [
            "Three source frames cannot establish a full physical delivery.",
            "A missing right time/colour candidate can reflect right-view censoring or timing mismatch.",
        ],
    }
    (args.output_dir / "manifest.json").write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps({"left_only_events": len(rows), "sheets": len(sheets)}))


if __name__ == "__main__":
    main()
