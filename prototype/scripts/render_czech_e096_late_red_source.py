"""Render E096's board-blind cap continuation from original source frames."""

from hashlib import sha256
import json
from pathlib import Path

import cv2
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark/canada-czech-2024"
VIDEO = BASE / "source-1080p-full-format270.mp4"
TRACK = BASE / "e096-late-red-board-continuation-development.json"
OUT = BASE / "e096-late-red-source-probe"


def digest(path):
    h = sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def main():
    if OUT.exists():
        raise ValueError("E096 late-red source packet already exists")
    track = json.loads(TRACK.read_text())
    if track["source_video_sha256"] != digest(VIDEO):
        raise ValueError("Track and source video differ")
    centers = [s["decision"]["selected"]["centroid_px_1080"]
               for s in track["steps"] if s["decision"]["selected"]]
    if not centers:
        raise ValueError("No E096 cap centers to render")
    x0 = max(0, int(min(p[0] for p in centers) - 95))
    x1 = min(1920, int(max(p[0] for p in centers) + 95))
    y0 = max(0, int(min(p[1] for p in centers) - 95))
    y1 = min(1080, int(max(p[1] for p in centers) + 95))
    roi = (x0, y0, x1, y1)
    cap = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG,
                           [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        raise ValueError("Source unreadable")
    pane_w, pane_h = 680, 500
    steps = track["steps"]
    sheet = Image.new("RGB", (2 * pane_w, ((len(steps) + 1) // 2) * pane_h),
                      "#eef1f5")
    try:
        for index, step in enumerate(steps):
            cap.set(cv2.CAP_PROP_POS_FRAMES, step["decoded_frame_index"])
            ok, frame = cap.read()
            if not ok or frame.shape[:2] != (1080, 1920):
                raise ValueError("Source frame unreadable")
            crop = Image.fromarray(cv2.cvtColor(frame[y0:y1, x0:x1],
                                                cv2.COLOR_BGR2RGB))
            scale = min((pane_w - 20) / crop.width,
                        (pane_h - 45) / crop.height)
            crop = crop.resize((round(crop.width * scale),
                                round(crop.height * scale)),
                               Image.Resampling.NEAREST)
            center = step["decision"]["selected"]["centroid_px_1080"]
            cx, cy = (center[0] - x0) * scale, (center[1] - y0) * scale
            draw = ImageDraw.Draw(crop)
            draw.ellipse((cx - 12, cy - 12, cx + 12, cy + 12),
                         outline="#00e8ff", width=4)
            pane = Image.new("RGB", (pane_w, pane_h), "white")
            pane.paste(crop, ((pane_w - crop.width) // 2, 38))
            ImageDraw.Draw(pane).text((10, 11),
                                      f"E096 source {step['source_time_s']:.1f} s"
                                      " | selected red cap", fill="black")
            sheet.paste(pane, ((index % 2) * pane_w,
                               (index // 2) * pane_h))
    finally:
        cap.release()
    OUT.mkdir(parents=True)
    sheet_path = OUT / "late-red-contact-sheet.jpg"
    sheet.save(sheet_path, quality=95)
    manifest = {
        "status": "e096_source_frames_for_same_agent_continuity_review",
        "source_video_sha256": track["source_video_sha256"],
        "track_sha256": digest(TRACK),
        "runner_sha256": digest(Path(__file__)),
        "roi_xyxy_px_1080": list(roi),
        "frame_count": len(steps),
        "frame_indices": [s["decoded_frame_index"] for s in steps],
        "sheet_sha256": digest(sheet_path),
        "marker_legend": "cyan ring: board-blind selected red cap centroid",
        "limitations": [
            "The crop excludes the static red stone farther right; compare full board frames in the source-backed board artifact.",
            "The contact sheet and cap sequence are same-agent evidence, not independent persistent stone identity validation.",
        ],
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"frames": len(steps), "sheet": str(sheet_path)}))


if __name__ == "__main__":
    main()
