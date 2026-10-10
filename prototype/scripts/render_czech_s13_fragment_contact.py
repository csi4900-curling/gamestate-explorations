"""Freeze S13 source frames around the possible red-stone contact and merge."""

from hashlib import sha256
import json
from pathlib import Path

import cv2
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark/canada-czech-2024"
VIDEO = BASE / "source-1080p-full-format270.mp4"
PROBE = BASE / "full-reviewed-stone-fragment-merge-continuations-development.json"
OUT = BASE / "s13-fragment-contact-source"
TIMES = (500.0, 500.5, 501.0, 501.5, 502.0, 502.5, 503.0, 504.0, 505.0)
CROP = (1200, 400, 1620, 660)


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def main():
    if OUT.exists():
        raise ValueError("S13 source packet already exists")
    probe = json.loads(PROBE.read_text())
    if digest(VIDEO) != probe["source_video_sha256"]:
        raise ValueError("Source video changed")
    row = next(item for item in probe["rows"] if item["episode_id"] == "E011")
    by_time = {step["source_time_s"]: step for step in row["steps"]}
    if any(t not in by_time for t in TIMES):
        raise ValueError("Probe lacks requested source times")
    cap = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened() or abs(cap.get(cv2.CAP_PROP_FPS) - 30) > 0.01:
        raise ValueError("Source video unreadable")
    OUT.mkdir(parents=True)
    sheet = Image.new("RGB", (3 * 420, 3 * 290), "white")
    draw = ImageDraw.Draw(sheet)
    frames = []
    try:
        for i, t in enumerate(TIMES):
            step = by_time[t]
            cap.set(cv2.CAP_PROP_POS_FRAMES, step["decoded_frame_index"])
            ok, frame = cap.read()
            if not ok or frame.shape[:2] != (1080, 1920):
                raise ValueError(f"Frame unreadable: {t}")
            x0, y0, x1, y1 = CROP
            crop = Image.fromarray(cv2.cvtColor(frame[y0:y1, x0:x1], cv2.COLOR_BGR2RGB))
            plain = OUT / f"source-crop-{t:.1f}.png"
            crop.save(plain)
            sx = (i % 3) * 420
            sy = (i // 3) * 290
            sheet.paste(crop, (sx, sy + 30))
            selected = step["decision"]["selected"]
            if selected:
                x, y = selected["centroid_px_1080"]
                cx, cy = sx + x - x0, sy + 30 + y - y0
                draw.ellipse((cx - 6, cy - 6, cx + 6, cy + 6), outline="yellow", width=2)
            marker = "merged" if step["fragment_merge_count"] else ""
            draw.text((sx + 6, sy + 7), f"{t:.1f} s  {marker}", fill="black")
            frames.append(
                {
                    "source_time_s": t,
                    "decoded_frame_index": step["decoded_frame_index"],
                    "unmarked_crop_file": plain.name,
                    "unmarked_crop_sha256": digest(plain),
                    "selected_cap_center_px_1080": selected["centroid_px_1080"]
                    if selected
                    else None,
                    "fragment_merge_count": step["fragment_merge_count"],
                }
            )
    finally:
        cap.release()
    sheet_path = OUT / "s13-500-505-contact-sheet.jpg"
    sheet.save(sheet_path, quality=92)
    (OUT / "manifest.json").write_text(
        json.dumps(
            {
                "status": "source_contact_sheet_for_agent_review_not_physical_identity_label",
                "source_video_sha256": probe["source_video_sha256"],
                "continuation_probe_sha256": digest(PROBE),
                "runner_sha256": digest(Path(__file__)),
                "crop_xyxy_px_1080": list(CROP),
                "contact_sheet_file": sheet_path.name,
                "contact_sheet_sha256": digest(sheet_path),
                "frames": frames,
                "limitations": [
                    "The marked centers are selected cap pixels, not verified physical stone identities.",
                    "The unmarked crops allow source review without predictions but omit the rest of the broadcast frame.",
                ],
            },
            indent=2,
        )
        + "\n"
    )
    print(json.dumps({"frames": len(frames), "contact_sheet": sheet_path.name}))


if __name__ == "__main__":
    main()
