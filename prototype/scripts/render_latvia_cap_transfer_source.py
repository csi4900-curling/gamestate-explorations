"""Render source packets for unchanged cap-continuation transfer cases."""

from hashlib import sha256
import json
from pathlib import Path

import cv2
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark/canada-latvia-2024"
VIDEO = BASE / "source-1080p-1650-2760.mp4"
TRACK = BASE / "board-blind-cap-continuation-transfer-development.json"
OUT = BASE / "board-blind-cap-continuation-source-probe"
IDS = ("S16", "S23", "S26")


def digest(path):
    h = sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def main():
    if OUT.exists():
        raise ValueError("Latvia cap transfer source packet already exists")
    track = json.loads(TRACK.read_text())
    if track["source_video_sha256"] != digest(VIDEO):
        raise ValueError("Latvia source or track changed")
    by_id = {r["candidate_id"]: r for r in track["rows"]}
    video = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not video.isOpened():
        raise ValueError("Latvia source unreadable")
    OUT.mkdir(parents=True)
    sheets = []
    try:
        for cid in IDS:
            row = by_id[cid]
            steps = row["steps"]
            centers = [
                s["decision"]["selected"]["centroid_px_1080"]
                for s in steps
                if s["decision"]["selected"]
            ]
            if len(centers) != len(steps):
                raise ValueError(f"Selected packet contains abstention: {cid}")
            x0 = max(0, int(min(p[0] for p in centers) - 95))
            x1 = min(1920, int(max(p[0] for p in centers) + 95))
            y0 = max(0, int(min(p[1] for p in centers) - 95))
            y1 = min(1080, int(max(p[1] for p in centers) + 95))
            pane_w, pane_h = 680, 500
            sheet = Image.new("RGB", (2 * pane_w, ((len(steps) + 1) // 2) * pane_h), "#eef1f5")
            for index, step in enumerate(steps):
                video.set(cv2.CAP_PROP_POS_FRAMES, step["decoded_interval_frame_index"])
                ok, frame = video.read()
                if not ok or frame.shape[:2] != (1080, 1920):
                    raise ValueError(f"Latvia source frame unreadable: {cid}")
                crop = Image.fromarray(cv2.cvtColor(frame[y0:y1, x0:x1], cv2.COLOR_BGR2RGB))
                scale = min((pane_w - 20) / crop.width, (pane_h - 45) / crop.height)
                crop = crop.resize(
                    (round(crop.width * scale), round(crop.height * scale)),
                    Image.Resampling.NEAREST,
                )
                x, y = centers[index]
                cx, cy = (x - x0) * scale, (y - y0) * scale
                ImageDraw.Draw(crop).ellipse(
                    (cx - 12, cy - 12, cx + 12, cy + 12), outline="#00e8ff", width=4
                )
                pane = Image.new("RGB", (pane_w, pane_h), "white")
                pane.paste(crop, ((pane_w - crop.width) // 2, 38))
                ImageDraw.Draw(pane).text(
                    (10, 11),
                    f"Latvia {cid} source {step['source_time_s']:.1f} s | selected cap",
                    fill="black",
                )
                sheet.paste(pane, ((index % 2) * pane_w, (index // 2) * pane_h))
            filename = f"{cid.lower()}-cap-continuation.jpg"
            sheet.save(OUT / filename, quality=95)
            sheets.append(
                {
                    "candidate_id": cid,
                    "sheet": filename,
                    "sheet_sha256": digest(OUT / filename),
                    "frame_count": len(steps),
                    "roi_xyxy_px_1080": [x0, y0, x1, y1],
                    "decoded_interval_frame_indices": [
                        s["decoded_interval_frame_index"] for s in steps
                    ],
                }
            )
    finally:
        video.release()
    manifest = {
        "status": "same_agent_cross_recording_source_review_not_identity_truth",
        "source_video_sha256": track["source_video_sha256"],
        "transfer_artifact_sha256": digest(TRACK),
        "runner_sha256": digest(Path(__file__)),
        "sheets": sheets,
        "marker_legend": "cyan ring: board-blind selected cap centroid",
        "limitations": [
            "Crops omit distant stones, people and view context outside the path corridor.",
            "The frames and judgments are post-transfer same-agent development review, not independent physical throw or identity labels.",
        ],
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"sheets": len(sheets), "output": str(OUT)}))


if __name__ == "__main__":
    main()
