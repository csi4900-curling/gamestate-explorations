"""Render full-source contact sheets for every Czech large-motion rejection."""

from hashlib import sha256
import json
from pathlib import Path

import cv2
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark"
VIDEO = BASE / "canada-czech-2024/source-360p.mp4"
RUN = BASE / "layout-router/czech24-full-camera-motion-v1"
RAW = RUN / "run-02/raw.json"
AUDIT = RUN / "large-surrounding-motion-rejections-development.json"
OUT = RUN / "large-motion-source-packet"


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def main():
    if OUT.exists():
        raise ValueError("Large-motion source packet already exists")
    raw, audit = (json.loads(path.read_text()) for path in (RAW, AUDIT))
    if (digest(VIDEO) != raw["source_sha256"] or
            audit["source_sha256"] != raw["source_sha256"] or
            audit["input_sha256"]["raw"] != digest(RAW)):
        raise ValueError("Source or input artifact mismatch")
    by_id = {row["id"]: row for row in raw["events"]}
    if len(audit["rows"]) != audit["large_surrounding_motion_rejection_count"]:
        raise ValueError("Rejection count mismatch")
    cap = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG,
                           [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        raise ValueError("Video unreadable")
    fps = cap.get(cv2.CAP_PROP_FPS)
    OUT.mkdir(parents=True)
    rows = []
    try:
        for audit_row in audit["rows"]:
            id = audit_row["candidate_id"]
            points = by_id[id]["observed_track_points"]
            if len(points) < 3:
                raise ValueError(f"Too few raw points: {id}")
            selected = [points[i] for i in (0, len(points)//2, len(points)-1)]
            sheet = Image.new("RGB", (3*640, 390), "white")
            draw = ImageDraw.Draw(sheet)
            frames = []
            for i, point in enumerate(selected):
                time_s = point["time_s"]
                cap.set(cv2.CAP_PROP_POS_FRAMES, round(time_s * fps))
                ok, frame = cap.read()
                if not ok or frame.shape[:2] != (360, 640):
                    raise ValueError(f"Frame unreadable: {id} {time_s}")
                image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                sheet.paste(image, (i*640, 30))
                x,y,w,h = point["bbox"]
                draw.rectangle((i*640+x, 30+y, i*640+x+w, 30+y+h),
                               outline="#ffff00", width=2)
                draw.text((i*640+8, 8), f"{id} | {time_s:.1f} s | {i+1}/3",
                          fill="black")
                frames.append({"source_time_s": time_s,
                               "video_frame_index": int(cap.get(
                                   cv2.CAP_PROP_POS_FRAMES)) - 1,
                               "raw_track_pixel": point["pixel"],
                               "raw_track_bbox": point["bbox"]})
            path = OUT / f"{id.lower()}-source-track.jpg"
            sheet.save(path, quality=92)
            rows.append({"candidate_id": id,
                         "changed_px_80x80": audit_row["changed_px_80x80"],
                         "file": path.name, "sha256": digest(path),
                         "frames": frames})
    finally:
        cap.release()
    (OUT / "manifest.json").write_text(json.dumps({
        "status": "candidate_selected_marked_source_sheets_not_independent_labels",
        "source_video_sha256": raw["source_sha256"],
        "input_sha256": {"raw": digest(RAW), "rejection_audit": digest(AUDIT)},
        "runner_sha256": digest(Path(__file__)),
        "rows": rows,
        "limitations": [
            "Yellow boxes mark raw detector coordinates, not verified stone centers.",
            "Three sampled source frames per candidate cannot establish a complete physical throw or exclude one.",
        ],
    }, indent=2) + "\n")
    print(json.dumps({"candidates": len(rows),
                      "sampled_source_frames": sum(len(row["frames"]) for row in rows)}))


if __name__ == "__main__":
    main()
