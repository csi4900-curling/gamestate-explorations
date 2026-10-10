"""Show source frames for selected motion-to-board continuation probes."""

from hashlib import sha256
import json
from pathlib import Path

import cv2
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark/canada-czech-2024"
VIDEO = BASE / "source-1080p-full-format270.mp4"
INVENTORY = BASE / "full-reviewed-settle-gap-cap-inventory-development.json"
OUT = BASE / "settle-gap-source-contact-sheets"
EPISODES = ("E001", "E011", "E080", "E096")


def digest(path):
    h = sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def main():
    if OUT.exists():
        raise ValueError("Settle-gap source contact sheets already exist")
    inventory = json.loads(INVENTORY.read_text())
    if inventory["source_video_sha256"] != digest(VIDEO):
        raise ValueError("Inventory and source video differ")
    by_episode = {row["episode_id"]: row for row in inventory["rows"]}
    cap = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        raise ValueError("Source video unreadable")
    OUT.mkdir(parents=True)
    outputs = []
    try:
        for eid in EPISODES:
            row = by_episode[eid]
            x0, y0, x1, y1 = row["roi_xyxy_px_1080"]
            pane_w, pane_h = 720, 480
            count = len(row["samples"])
            sheet = Image.new("RGB", (2 * pane_w, ((count + 1) // 2) * pane_h), "#eff3f6")
            for index, sample in enumerate(row["samples"]):
                cap.set(cv2.CAP_PROP_POS_FRAMES, sample["decoded_frame_index"])
                ok, frame = cap.read()
                if not ok or frame.shape[:2] != (1080, 1920):
                    raise ValueError("Source frame unreadable")
                source = Image.fromarray(cv2.cvtColor(frame[y0:y1, x0:x1], cv2.COLOR_BGR2RGB))
                scale = min((pane_w - 20) / source.width, (pane_h - 46) / source.height)
                display = source.resize(
                    (round(source.width * scale), round(source.height * scale)),
                    Image.Resampling.NEAREST,
                )
                draw = ImageDraw.Draw(display)
                for component_index, component in enumerate(
                    sample["same_colour_components"], start=1
                ):
                    x, y = component["centroid_px_1080"]
                    cx, cy = (x - x0) * scale, (y - y0) * scale
                    draw.ellipse((cx - 10, cy - 10, cx + 10, cy + 10), outline="#f000ef", width=3)
                    draw.text(
                        (cx + 10, cy - 10),
                        str(component_index),
                        fill="#f000ef",
                        stroke_width=2,
                        stroke_fill="white",
                    )
                pane = Image.new("RGB", (pane_w, pane_h), "white")
                pane.paste(display, ((pane_w - display.width) // 2, 38))
                ImageDraw.Draw(pane).text(
                    (10, 11),
                    f"{eid} source {sample['source_time_s']:.2f} s"
                    f" | {len(sample['same_colour_components'])}"
                    " same-colour components",
                    fill="black",
                )
                sheet.paste(pane, ((index % 2) * pane_w, (index // 2) * pane_h))
            name = f"{eid.lower()}-source-contact-sheet.jpg"
            sheet.save(OUT / name, quality=95)
            outputs.append(
                {
                    "episode_id": eid,
                    "sheet": name,
                    "sheet_sha256": digest(OUT / name),
                    "sample_count": count,
                    "source_roi_xyxy_px_1080": [x0, y0, x1, y1],
                }
            )
    finally:
        cap.release()
    manifest = {
        "status": "same_agent_source_review_packet_not_persistent_identity_truth",
        "source_video_sha256": inventory["source_video_sha256"],
        "inventory_sha256": digest(INVENTORY),
        "runner_sha256": digest(Path(__file__)),
        "sheets": outputs,
        "marker_legend": "Magenta rings mark every same-colour HSV component in the ROI, ordered by area; numbers are frame-local only.",
        "limitations": [
            "The displayed ROI is derived from the last motion point and first same-colour board proposals; off-crop stones and camera context are omitted.",
            "Frame-local component numbers do not assert persistent identity.",
            "These are same-agent development packets, not independent throw or stone labels.",
        ],
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"sheets": len(outputs), "output": str(OUT)}))


if __name__ == "__main__":
    main()
