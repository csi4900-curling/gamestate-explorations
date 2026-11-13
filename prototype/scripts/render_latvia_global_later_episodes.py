"""Render every quiet-separated later global right proposal in source frames."""

from hashlib import sha256
import json
from pathlib import Path

import cv2
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark/canada-latvia-2024"
VIDEO = BASE / "source-360p.mp4"
PROBE = BASE / "full-right-global-multi-episode-development.json"
OUT = BASE / "full-right-global-later-episode-source-packet"


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def main():
    if OUT.exists():
        raise ValueError("Later-episode source packet already exists")
    probe = json.loads(PROBE.read_text())
    if probe["source_sha256"] != digest(VIDEO) or len(probe["later_review_proposals"]) != 4:
        raise ValueError("Later-episode source or inventory differs")
    cap = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    fps = cap.get(cv2.CAP_PROP_FPS)
    if not cap.isOpened() or fps <= 0:
        raise ValueError("Source video unreadable")
    OUT.mkdir(parents=True)
    rows, pages = [], []
    try:
        for page_index, start in enumerate(range(0, 4, 2), 1):
            chunk = probe["later_review_proposals"][start : start + 2]
            sheet = Image.new("RGB", (960, 1008), "white")
            for row_index, proposal in enumerate(chunk):
                points = proposal["observed_prefix_points"]
                if len(points) < 3:
                    raise ValueError("Later episode has too few observed points")
                samples = [points[index] for index in (0, len(points) // 2, len(points) - 1)]
                for sample_index, point in enumerate(samples):
                    cap.set(cv2.CAP_PROP_POS_FRAMES, round(point["time_s"] * fps))
                    ok, frame = cap.read()
                    if not ok or frame.shape[:2] != (360, 640):
                        raise ValueError("Later-episode source frame unreadable")
                    source = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                    panel = source.crop((320, 0, 640, 360))
                    draw = ImageDraw.Draw(panel)
                    x, y, w, h = point["bbox"]
                    draw.rectangle(
                        (x - 325, y - 5, x - 315 + w, y + h + 5), outline="magenta", width=3
                    )
                    draw.rectangle((0, 0, 150, 22), fill="white")
                    draw.text(
                        (3, 4),
                        f"{proposal['raw_track_id']} #{proposal['episode_index_within_raw_track']} {point['time_s']:.0f}s",
                        fill="red",
                    )
                    px, py = point["pixel"]
                    crop = source.crop(
                        (int(px) - 32, int(py) - 32, int(px) + 32, int(py) + 32)
                    ).resize((144, 144), Image.Resampling.NEAREST)
                    left, top = sample_index * 320, row_index * 504
                    sheet.paste(panel, (left, top))
                    sheet.paste(crop, (left + 88, top + 360))
                rows.append(
                    {
                        "raw_track_id": proposal["raw_track_id"],
                        "episode_index_within_raw_track": proposal[
                            "episode_index_within_raw_track"
                        ],
                        "passage_time_s": proposal["passage"]["time_s"],
                        "colour_claim": proposal["colour_claim"],
                        "direction": proposal["direction"],
                        "source_sample_times_s": [point["time_s"] for point in samples],
                        "review_page": f"later-page-{page_index}.jpg",
                    }
                )
            page = OUT / f"later-page-{page_index}.jpg"
            sheet.save(page, quality=93)
            pages.append(
                {"image": page.name, "sha256": digest(page), "candidate_count": len(chunk)}
            )
    finally:
        cap.release()
    result = {
        "status": "postinspection_all_later_global_episode_source_packet_not_throw_truth",
        "source_video_sha256": digest(VIDEO),
        "multi_episode_probe_sha256": digest(PROBE),
        "runner_sha256": digest(Path(__file__)),
        "rows": rows,
        "pages": pages,
        "limitations": [
            "The four later episodes were generated after the global A452 miss was inspected.",
            "Three frames per proposal show tracked source pixels, not physical event identity or a settled board.",
        ],
    }
    (OUT / "manifest.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"later_episodes": len(rows), "pages": len(pages)}))


if __name__ == "__main__":
    main()
