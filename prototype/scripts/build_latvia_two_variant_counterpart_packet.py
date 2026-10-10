"""Render source evidence for the unreviewed member of each two-variant group."""

from hashlib import sha256
import json
from pathlib import Path

import cv2
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark/canada-latvia-2024"
VIDEO = BASE / "source-360p.mp4"
QUEUE = BASE / "full-right-variant-review-queue-development.json"
SCANS = {
    "two_second_global": BASE / "full-right-global-area-development.json",
    "two_second_greedy": BASE / "full-right-area-gap2-development.json",
}
OUT = BASE / "full-right-two-variant-counterpart-source-packet"
COUNTERPART_IDS = {
    "R0042": "two_second_global:A184:1",
    "R0062": "two_second_global:A315:1",
    "R0065": "two_second_global:A323:1",
    "R0071": "two_second_global:A358:1",
    "R0079": "two_second_global:A391:1",
    "R0082": "two_second_global:A399:1",
    "R0090": "two_second_greedy:A425:1",
    "R0091": "two_second_global:A429:1",
    "R0092": "two_second_global:A434:1",
    "R0093": "two_second_global:A440:1",
    "R0102": "two_second_global:A484:1",
}


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def main():
    queue = json.loads(QUEUE.read_text())
    scans = {name: json.loads(path.read_text()) for name, path in SCANS.items()}
    video_hash = digest(VIDEO)
    if (queue["source_video_sha256"] != video_hash or
            any(scan["source_sha256"] != video_hash or
                queue["input_sha256"][name] != digest(SCANS[name])
                for name, scan in scans.items())):
        raise ValueError("Video, queue or scan lineage differs")
    pairs = {g["group_id"]: g for g in queue["review_groups"] if len({
        pid.split(":")[0] for pid in g["proposal_ids"]}) == 2}
    if set(pairs) != set(COUNTERPART_IDS) or any(
            COUNTERPART_IDS[gid] not in group["proposal_ids"]
            for gid, group in pairs.items()):
        raise ValueError("Two-variant inventory changed")
    proposal_rows = {f"{name}:{row['raw_track_id']}:1": row
                     for name, scan in scans.items()
                     for row in scan["directional_review_proposals"]}
    raw_tracks = {name: {row["track_id"]: row for row in scan["raw_tracks"]}
                  for name, scan in scans.items()}
    if OUT.exists():
        raise ValueError("Source packet exists")
    capture = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG,
                               [cv2.CAP_PROP_N_THREADS, 1])
    fps = capture.get(cv2.CAP_PROP_FPS)
    if not capture.isOpened() or fps <= 0:
        raise ValueError("Source unreadable")
    OUT.mkdir(parents=True)
    items = list(COUNTERPART_IDS.items())
    rows = []
    try:
        for page_index, start in enumerate(range(0, len(items), 3), 1):
            chunk = items[start:start + 3]
            sheet = Image.new("RGB", (960, 504 * len(chunk)), "white")
            for row_index, (group_id, pid) in enumerate(chunk):
                variant, track, _ = pid.split(":")
                proposal = proposal_rows[pid]
                time = proposal["passage"]["time_s"]
                points = proposal["observed_prefix_points"]
                if len(points) < 3:
                    points = raw_tracks[variant][track]["points"]
                    sampling_policy = "nearest_three_raw_track_points"
                else:
                    sampling_policy = "nearest_three_prefix_points"
                samples = sorted(sorted(points, key=lambda p: (
                    abs(p["time_s"] - time), p["time_s"]))[:3],
                                 key=lambda p: p["time_s"])
                if len(samples) != 3:
                    raise ValueError("Too few source points")
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
                    draw.rectangle((0, 0, 190, 22), fill="white")
                    draw.text((3, 4), f"{group_id} {track} {point['time_s']:.0f}s",
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
                rows.append({"review_group_id": group_id, "proposal_id": pid,
                             "passage_time_s": time,
                             "sample_times_s": [p["time_s"] for p in samples],
                             "sampling_policy": sampling_policy,
                             "page": f"page-{page_index}.jpg"})
            sheet.save(OUT / f"page-{page_index}.jpg", quality=93)
    finally:
        capture.release()
    result = {"status": "postproposal_two_variant_source_packet_not_throw_truth",
              "source_video_sha256": video_hash,
              "review_queue_sha256": digest(QUEUE),
              "scan_sha256": {name: digest(path) for name, path in SCANS.items()},
              "runner_sha256": digest(Path(__file__)),
              "selection": "Previously unreviewed member of each 11 two-variant review groups",
              "rows": rows,
              "page_sha256": {p.name: digest(p) for p in OUT.glob("page-*.jpg")}}
    (OUT / "manifest.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"proposals": len(rows), "pages": len(result["page_sha256"])}))


if __name__ == "__main__":
    main()
