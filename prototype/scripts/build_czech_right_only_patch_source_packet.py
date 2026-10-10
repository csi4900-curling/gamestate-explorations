"""Render every Czech right-only proposal at the frozen patch-score samples."""

from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cap_patch_verifier import context_bbox

BASE = ROOT / "validation/throw-event-benchmark/canada-czech-2024"
VIDEO = BASE / "source-360p.mp4"
SCORES = BASE / "full-right-source-diverse-patch-transfer-development.json"
EPISODES = BASE / "full-corridor-right-episodes-first-transfer.json"
OUT = BASE / "full-right-only-source-diverse-review-packet"


def digest(path):
    h = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    if OUT.exists():
        raise ValueError("Right-only source packet already exists")
    scores = json.loads(SCORES.read_text())
    episodes = json.loads(EPISODES.read_text())
    video_hash = digest(VIDEO)
    if (scores["source_video_sha256"] != video_hash or
            episodes["source_sha256"] != video_hash or
            episodes["right_tail_sha256"] != scores["input_sha256"]["scan"]):
        raise ValueError("Source or episode lineage differs")
    right_only = [(ep["episode_id"], ep["right_proposal_ids"][0])
                  for ep in episodes["episodes"]
                  if ep["episode_kind"] == "right_only_candidate"]
    if len(right_only) != 23 or len({pid for _, pid in right_only}) != 23:
        raise ValueError("Right-only inventory changed")
    by_id = {row["right_proposal_id"]: row for row in scores["rows"]}
    if len(by_id) != scores["proposal_count"]:
        raise ValueError("Duplicate scored proposal ID")
    capture = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG,
                               [cv2.CAP_PROP_N_THREADS, 1])
    fps = capture.get(cv2.CAP_PROP_FPS)
    if not capture.isOpened() or fps <= 0:
        raise ValueError("Czech source unreadable")
    OUT.mkdir(parents=True)
    rows = []
    try:
        for page_index, start in enumerate(range(0, 23, 3), 1):
            page = Image.new("RGB", (960, 504 * len(right_only[start:start + 3])),
                             "white")
            for row_index, (episode_id, pid) in enumerate(right_only[start:start + 3]):
                score = by_id[pid]
                for sample_index, sample in enumerate(score["samples"]):
                    time = sample["time_s"]
                    capture.set(cv2.CAP_PROP_POS_FRAMES, round(time * fps))
                    ok, frame = capture.read()
                    if not ok or frame.shape[:2] != (360, 640):
                        raise ValueError(f"Unreadable source frame: {pid} {time}")
                    panel = Image.fromarray(cv2.cvtColor(frame[:, 320:],
                                                         cv2.COLOR_BGR2RGB))
                    draw = ImageDraw.Draw(panel)
                    x, y, w, h = sample["cap_bbox_px"]
                    draw.rectangle((x - 325, y - 5, x + w - 315, y + h + 5),
                                   outline="magenta", width=3)
                    bx, by, side, _ = context_bbox(sample["cap_bbox_px"])
                    draw.rectangle((bx - 320, by, bx + side - 320, by + side),
                                   outline="cyan", width=2)
                    draw.rectangle((0, 0, 260, 22), fill="white")
                    draw.text((3, 4),
                              f"{episode_id} {pid} {time:.0f}s score {sample['patch_score']:.2f}",
                              fill="black")
                    source = Image.fromarray(cv2.cvtColor(frame,
                                                           cv2.COLOR_BGR2RGB))
                    crop = source.crop((bx, by, bx + side, by + side))
                    crop = crop.resize((144, 144), Image.Resampling.NEAREST)
                    left, top = sample_index * 320, row_index * 504
                    page.paste(panel, (left, top))
                    page.paste(crop, (left + 88, top + 360))
                rows.append({
                    "episode_id": episode_id,
                    "right_proposal_id": pid,
                    "source_sample_times_s": [s["time_s"] for s in score["samples"]],
                    "positive_patch_count": score["positive_patch_count"],
                    "page": f"page-{page_index}.jpg",
                })
            page.save(OUT / f"page-{page_index}.jpg", quality=93)
    finally:
        capture.release()
    manifest = {
        "status": "fixed_all_right_only_source_pixel_review_packet_not_event_truth",
        "source_video_sha256": video_hash,
        "input_sha256": {"scores": digest(SCORES), "episodes": digest(EPISODES)},
        "context_geometry_code_sha256": digest(ROOT / "prototype/cap_patch_verifier.py"),
        "runner_sha256": digest(Path(__file__)),
        "rows": rows,
        "page_sha256": {p.name: digest(p) for p in sorted(OUT.glob("page-*.jpg"))},
        "limitations": [
            "Three sampled prefix frames, or two for one short track, do not establish whole-track identity.",
            "Right-only episode status is temporal association, not proof of a missed left-camera throw.",
            "Source-pixel labels on these pages are same-agent postscore development review, not independent physical-event truth.",
        ],
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"proposals": len(rows), "pages": len(manifest["page_sha256"])}))


if __name__ == "__main__":
    main()
