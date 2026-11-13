"""Render source frames for two-view China throw-colour revisions."""

from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.scripts.scan_china_full_match_boards import read_frame

VIDEO = ROOT / "validation/throw-event-benchmark/paralympics-2022-canada-china/source.mp4"
DEMO = ROOT / "prototype/full-match-canada-china/results.json"
BASE = ROOT / "validation/official-shot-sequence"
OUTPUT = BASE / "china-two-view-colour-revisions.png"
PROVENANCE = BASE / "china-two-view-colour-revisions.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    if OUTPUT.exists() or PROVENANCE.exists():
        raise SystemExit("Output exists; preserve first colour-revision audit")
    demo = json.loads(DEMO.read_text())
    if demo["source_video_sha256"] != digest(VIDEO):
        raise ValueError("Demo and source video differ")
    revised = [
        row
        for row in demo["events"]
        if row["colour_reconciliation"]["status"]
        in ("source_two_view_colour_filled", "source_two_view_colour_corrected")
    ]
    if len(revised) != 2:
        raise ValueError("Expected two China source-cue colour revisions")
    canvas = Image.new("RGB", (3 * 640, 2 * 390), "#f3f5f4")
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    cap = cv2.VideoCapture(str(VIDEO))
    fps = cap.get(cv2.CAP_PROP_FPS)
    rows = []
    try:
        for row_i, event in enumerate(revised):
            cue = event["release_cue"]["time_s"]
            times = [cue - 2, cue, cue + 4]
            for column, time_s in enumerate(times):
                frame = read_frame(cap, fps, time_s)
                if frame is None:
                    raise RuntimeError(f"Missing frame at {time_s}")
                x, y = column * 640, row_i * 390
                canvas.paste(Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)), (x, y + 30))
                draw.text(
                    (x + 10, y + 8),
                    f"{event['id']} · {time_s:.1f}s · "
                    f"{event['colour_reconciliation']['original_colour']} → {event['colour']}",
                    fill="#172b27",
                    font=font,
                )
            rows.append(
                {
                    "event_id": event["id"],
                    "original_colour": event["colour_reconciliation"]["original_colour"],
                    "reconciled_colour": event["colour"],
                    "release_cue_colour": event["release_cue"]["colour"],
                    "receiving_view_colour": event["receiving_view"]["colour"],
                    "sample_times_s": times,
                }
            )
    finally:
        cap.release()
    canvas.save(OUTPUT)
    record = {
        "status": "source_frame_illustration_of_two_view_colour_revisions",
        "source_video_sha256": digest(VIDEO),
        "demo_sha256": digest(DEMO),
        "runner_sha256": digest(Path(__file__)),
        "output_sha256": digest(OUTPUT),
        "rows": rows,
        "limitations": [
            "Source frames illustrate the cue colour; they do not independently verify cross-camera physical stone identity.",
            "The two-view colour rule did not use official diagrams or manual shot labels.",
        ],
    }
    PROVENANCE.write_text(json.dumps(record, indent=2) + "\n")
    print({"revised_events": len(rows), "output": str(OUTPUT)})


if __name__ == "__main__":
    main()
