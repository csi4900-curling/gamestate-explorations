"""Render source-frame evidence for global-only first-episode review groups."""

from hashlib import sha256
import json
from pathlib import Path

import cv2
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark/canada-latvia-2024"
VIDEO = BASE / "source-360p.mp4"
SCAN = BASE / "full-right-global-area-development.json"
QUEUE = BASE / "full-right-variant-review-queue-development.json"
OUT = BASE / "full-right-global-singleton-source-packet"
IDS = ("A083", "A217", "A497", "A530")


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def main():
    scan, queue = json.loads(SCAN.read_text()), json.loads(QUEUE.read_text())
    video_hash = digest(VIDEO)
    if (scan["source_sha256"] != queue["source_video_sha256"] or
            queue["source_video_sha256"] != video_hash):
        raise ValueError("Source mismatch")
    if queue["input_sha256"]["two_second_global"] != digest(SCAN):
        raise ValueError("Queue lineage mismatch")
    proposals = {row["raw_track_id"]: row for row in scan[
        "directional_review_proposals"] if row["raw_track_id"] in IDS}
    if set(proposals) != set(IDS):
        raise ValueError("Global-only proposal inventory mismatch")
    singleton_ids = {g["proposal_ids"][0] for g in queue["review_groups"]
                     if len(g["proposal_ids"]) == 1}
    if not all(f"two_second_global:{track}:1" in singleton_ids for track in IDS):
        raise ValueError("One of the selected proposals is no longer singleton")
    if OUT.exists():
        raise ValueError("Source packet exists")
    capture = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG,
                               [cv2.CAP_PROP_N_THREADS, 1])
    fps = capture.get(cv2.CAP_PROP_FPS)
    if not capture.isOpened() or fps <= 0:
        raise ValueError("Source unreadable")
    OUT.mkdir(parents=True)
    manifest = []
    try:
        for page_index, ids in enumerate((IDS[:2], IDS[2:]), 1):
            sheet = Image.new("RGB", (960, 1008), "white")
            for row_index, track_id in enumerate(ids):
                proposal = proposals[track_id]
                points = proposal["observed_prefix_points"]
                time = proposal["passage"]["time_s"]
                samples = sorted(sorted(points, key=lambda p: (
                    abs(p["time_s"] - time), p["time_s"]))[:3],
                                 key=lambda p: p["time_s"])
                if len(samples) != 3:
                    raise ValueError("Too few prefix points")
                for sample_index, point in enumerate(samples):
                    capture.set(cv2.CAP_PROP_POS_FRAMES,
                                round(point["time_s"] * fps))
                    ok, frame = capture.read()
                    if not ok or frame.shape[:2] != (360, 640):
                        raise ValueError("Could not decode source frame")
                    panel = Image.fromarray(cv2.cvtColor(frame[:, 320:],
                                                         cv2.COLOR_BGR2RGB))
                    draw = ImageDraw.Draw(panel)
                    x, y, w, h = point["bbox"]
                    draw.rectangle((x - 325, y - 5, x - 315 + w, y + h + 5),
                                   outline="magenta", width=3)
                    draw.rectangle((0, 0, 170, 22), fill="white")
                    draw.text((3, 4), f"{track_id} {point['time_s']:.0f}s",
                              fill="red")
                    source = Image.fromarray(cv2.cvtColor(frame,
                                                           cv2.COLOR_BGR2RGB))
                    px, py = point["pixel"]
                    crop = source.crop((int(px) - 32, int(py) - 32,
                                        int(px) + 32, int(py) + 32))
                    crop = crop.resize((144, 144), Image.Resampling.NEAREST)
                    left, top = sample_index * 320, row_index * 504
                    sheet.paste(panel, (left, top))
                    sheet.paste(crop, (left + 88, top + 360))
                manifest.append({"raw_track_id": track_id,
                                 "passage_time_s": time,
                                 "colour_claim": proposal["colour_claim"],
                                 "direction": proposal["direction"],
                                 "sample_times_s": [p["time_s"] for p in samples],
                                 "page": f"page-{page_index}.jpg"})
            sheet.save(OUT / f"page-{page_index}.jpg", quality=93)
    finally:
        capture.release()
    result = {"status": "postproposal_source_pixel_packet_not_throw_truth",
              "source_video_sha256": video_hash,
              "global_scan_sha256": digest(SCAN),
              "review_queue_sha256": digest(QUEUE),
              "runner_sha256": digest(Path(__file__)),
              "selection": "All four first-episode two-second-global-only review groups",
              "rows": manifest,
              "page_sha256": {p.name: digest(p) for p in OUT.glob("page-*.jpg")}}
    (OUT / "manifest.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"proposals": len(manifest), "pages": 2}))


if __name__ == "__main__":
    main()
