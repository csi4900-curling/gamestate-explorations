"""Render source frames for every temporally novel full-match gap-two proposal."""

from hashlib import sha256
import json
from pathlib import Path

import cv2
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark/canada-latvia-2024"
VIDEO = BASE / "source-360p.mp4"
OLD = BASE / "full-right-area-first-transfer.json"
NEW = BASE / "full-right-area-gap2-development.json"
OUT = BASE / "full-right-gap2-novel-source-packet"
WINDOW_S = 8


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def proposal_time(row):
    return row["passage"]["time_s"]


def novel_proposals(old, new):
    return [
        row
        for row in new
        if not any(
            prior["colour_claim"] == row["colour_claim"]
            and prior["direction"] == row["direction"]
            and abs(proposal_time(prior) - proposal_time(row)) <= WINDOW_S
            for prior in old
        )
    ]


def main():
    if OUT.exists():
        raise ValueError("Novel gap-two source packet already exists")
    old = json.loads(OLD.read_text())
    new = json.loads(NEW.read_text())
    if not old["source_sha256"] == new["source_sha256"] == digest(VIDEO):
        raise ValueError("Gap-one, gap-two and source fingerprints differ")
    proposals = novel_proposals(
        old["directional_review_proposals"], new["directional_review_proposals"]
    )
    proposals.sort(key=lambda row: proposal_time(row))
    if len(proposals) != 15 or any(row["colour_claim"] != "red" for row in proposals):
        raise ValueError("Frozen novel gap-two proposal inventory differs")
    cap = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    fps = cap.get(cv2.CAP_PROP_FPS)
    if not cap.isOpened() or fps <= 0:
        raise ValueError("Source video unreadable")
    OUT.mkdir(parents=True)
    rows, pages = [], []
    try:
        for page_index, start in enumerate(range(0, len(proposals), 3), 1):
            chunk = proposals[start : start + 3]
            sheet = Image.new("RGB", (960, 504 * len(chunk)), "white")
            for row_index, proposal in enumerate(chunk):
                points = proposal["observed_prefix_points"]
                if len(points) < 3:
                    matching = [
                        row
                        for row in new["raw_tracks"]
                        if row["track_id"] == proposal["raw_track_id"]
                    ]
                    if len(matching) != 1:
                        raise ValueError("Novel short-prefix track is not unique")
                    samples = sorted(
                        sorted(
                            matching[0]["points"],
                            key=lambda p: (abs(p["time_s"] - proposal_time(proposal)), p["time_s"]),
                        )[:3],
                        key=lambda p: p["time_s"],
                    )
                    sampling_policy = "nearest_three_raw_track_points_fallback"
                else:
                    samples = [
                        points[i] for i in sorted(set((0, len(points) // 2, len(points) - 1)))
                    ]
                    sampling_policy = "first_middle_last_proposal_prefix"
                if len(samples) != 3:
                    raise ValueError("Novel path has duplicate sample indices")
                for sample_index, point in enumerate(samples):
                    cap.set(cv2.CAP_PROP_POS_FRAMES, round(point["time_s"] * fps))
                    ok, frame = cap.read()
                    if not ok or frame.shape[:2] != (360, 640):
                        raise ValueError("Source frame unreadable")
                    panel = Image.fromarray(cv2.cvtColor(frame[:, 320:], cv2.COLOR_BGR2RGB))
                    draw = ImageDraw.Draw(panel)
                    x, y, w, h = point["bbox"]
                    draw.rectangle(
                        (x - 325, y - 5, x - 315 + w, y + h + 5), outline="magenta", width=3
                    )
                    draw.rectangle((0, 0, 150, 22), fill="white")
                    draw.text(
                        (3, 4), f"{proposal['raw_track_id']} {point['time_s']:.0f}s", fill="red"
                    )
                    source = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                    px, py = point["pixel"]
                    crop = source.crop((int(px) - 32, int(py) - 32, int(px) + 32, int(py) + 32))
                    crop = crop.resize((144, 144), Image.Resampling.NEAREST)
                    left = sample_index * 320
                    top = row_index * 504
                    sheet.paste(panel, (left, top))
                    sheet.paste(crop, (left + 88, top + 360))
                rows.append(
                    {
                        "raw_track_id": proposal["raw_track_id"],
                        "passage_time_s": proposal_time(proposal),
                        "colour_claim": proposal["colour_claim"],
                        "direction": proposal["direction"],
                        "observed_prefix_points": points,
                        "source_sample_times_s": [p["time_s"] for p in samples],
                        "sampling_policy": sampling_policy,
                        "review_page": f"novel-page-{page_index}.jpg",
                    }
                )
            page = OUT / f"novel-page-{page_index}.jpg"
            sheet.save(page, quality=93)
            pages.append(
                {"image": page.name, "sha256": digest(page), "candidate_count": len(chunk)}
            )
    finally:
        cap.release()
    result = {
        "status": "development_all_temporally_novel_full_gap2_source_packet_not_throw_truth",
        "source_video_sha256": digest(VIDEO),
        "one_second_gap_scan_sha256": digest(OLD),
        "two_second_gap_scan_sha256": digest(NEW),
        "runner_sha256": digest(Path(__file__)),
        "novelty_rule": "no same-colour same-direction gap-one passage within 8 seconds",
        "novelty_window_s": WINDOW_S,
        "rows": rows,
        "pages": pages,
        "limitations": [
            "Novel means temporally unmatched under a development comparison, not a new physical throw.",
            "Three proposal-prefix samples do not prove full-track identity, release or settle.",
            "This gap-two full-source test was run after the R008 miss was known on Latvia.",
        ],
    }
    (OUT / "manifest.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"novel_proposals": len(rows), "pages": len(pages)}))


if __name__ == "__main__":
    main()
