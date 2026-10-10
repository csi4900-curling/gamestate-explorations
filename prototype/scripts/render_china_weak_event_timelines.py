"""Sample four visual-only China event windows at fixed three-second steps."""

from hashlib import sha256
import json
from math import ceil
from pathlib import Path
import sys

import cv2
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.scripts.scan_china_full_match_boards import read_frame

VIDEO = ROOT / "validation/throw-event-benchmark/paralympics-2022-canada-china/source.mp4"
EVENTS = (
    ROOT
    / "validation/official-shot-sequence/pwg2022-full-match-event-review-segments-v3-preorigin-travel-development.json"
)
OUTPUT = ROOT / "validation/official-shot-sequence/china-weak-event-timelines"
MANIFEST = OUTPUT / "manifest.json"
IDS = ("VISUAL-S52", "VISUAL-S360", "VISUAL-S403", "VISUAL-S411")
STEP_S = 3
FRAMES_PER_PAGE = 8


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def times_for_window(window):
    start = int(window[0] - 6)
    end = int(window[1] + 9)
    return list(range(start, end + 1, STEP_S))


def main():
    if MANIFEST.exists():
        raise SystemExit("Weak-event timeline audit exists; preserve first source sample")
    source = json.loads(EVENTS.read_text())
    game = next(g for g in source["games"] if g["official_game_code"] == "PREL000102")
    if game["source_sha256"] != digest(VIDEO):
        raise ValueError("Review and source video differ")
    selected = {s["event_id"]: s for s in game["segments"] if s["event_id"] in IDS}
    if set(selected) != set(IDS) or any(selected[key]["counter_id"] is not None for key in IDS):
        raise ValueError("Visual-only candidate inventory changed")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(VIDEO))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open {VIDEO}")
    fps = cap.get(cv2.CAP_PROP_FPS)
    font = ImageFont.load_default()
    rows = []
    try:
        for event_id in IDS:
            event = selected[event_id]
            times = times_for_window(event["delivery_window_s"])
            pages = []
            for page_index in range(ceil(len(times) / FRAMES_PER_PAGE)):
                chunk = times[page_index * FRAMES_PER_PAGE : (page_index + 1) * FRAMES_PER_PAGE]
                sheet = Image.new("RGB", (1280, 4 * 390), "#f2f4f3")
                draw = ImageDraw.Draw(sheet)
                for i, time_s in enumerate(chunk):
                    frame = read_frame(cap, fps, time_s)
                    if frame is None:
                        raise RuntimeError(f"Frame unavailable at {time_s}")
                    x, y = (i % 2) * 640, (i // 2) * 390
                    sheet.paste(
                        Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)), (x, y + 30)
                    )
                    boundary = (
                        "before"
                        if time_s < event["delivery_window_s"][0]
                        else "after"
                        if time_s > event["delivery_window_s"][1]
                        else "inside"
                    )
                    draw.text(
                        (x + 9, y + 8),
                        f"{event_id} · {time_s}s · {boundary}",
                        fill="#172b27",
                        font=font,
                    )
                filename = f"{event_id.lower()}-{page_index + 1:02}.png"
                sheet.save(OUTPUT / filename)
                pages.append(
                    {"file": filename, "sha256": digest(OUTPUT / filename), "sample_times_s": chunk}
                )
            rows.append(
                {
                    "event_id": event_id,
                    "delivery_window_s": event["delivery_window_s"],
                    "review_window_s": event["review_window_s"],
                    "camera_shots": event["review_shot_ids"],
                    "sample_times_s": times,
                    "pages": pages,
                }
            )
    finally:
        cap.release()
    result = {
        "status": "source_only_three_second_weak_event_timeline_audit",
        "source_video_sha256": digest(VIDEO),
        "review_sha256": digest(EVENTS),
        "runner_sha256": digest(Path(__file__)),
        "sample_step_s": STEP_S,
        "event_count": len(rows),
        "rows": rows,
        "limitations": [
            "Three-second samples can miss a brief delivery or camera cut.",
            "No official shot positions, counts, or labels entered selection.",
            "These images do not independently label true/false throws.",
        ],
    }
    MANIFEST.write_text(json.dumps(result, indent=2) + "\n")
    print({"events": len(rows), "pages": sum(len(r["pages"]) for r in rows), "output": str(OUTPUT)})


if __name__ == "__main__":
    main()
