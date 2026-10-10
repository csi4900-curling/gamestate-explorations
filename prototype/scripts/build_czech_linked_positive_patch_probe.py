"""Render a frozen sample of Czech positive one-to-one right-camera links."""

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
OUT = BASE / "full-linked-positive-patch-source-probe"


def digest(path):
    h = sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def select(scores, episodes):
    by_id = {row["right_proposal_id"]: row for row in scores["rows"]}
    eligible = []
    for episode in episodes["episodes"]:
        if episode["episode_kind"] != "one_to_one_time_candidate":
            continue
        pid = episode["right_proposal_ids"][0]
        if by_id[pid]["any_positive_patch"]:
            eligible.append((episode["episode_id"], pid))
    eligible.sort(key=lambda item: (by_id[item[1]]["passage_time_s"], item[1]))
    if len(eligible) != 90:
        raise ValueError("Positive one-to-one inventory changed")
    chosen = {}
    for i in range(12):
        episode_id, pid = eligible[round(i * (len(eligible) - 1) / 11)]
        chosen[pid] = (episode_id, "time_spaced")
    remaining = [item for item in eligible if item[1] not in chosen]
    remaining.sort(
        key=lambda item: (
            sum(s["patch_score"] for s in by_id[item[1]]["samples"])
            / len(by_id[item[1]]["samples"]),
            item[1],
        )
    )
    for episode_id, pid in remaining[:8]:
        chosen[pid] = (episode_id, "lowest_mean_score_remaining")
    if len(chosen) != 20:
        raise ValueError("Positive probe selection changed")
    return sorted(
        ((episode_id, pid, kind) for pid, (episode_id, kind) in chosen.items()),
        key=lambda item: (by_id[item[1]]["passage_time_s"], item[1]),
    )


def main():
    if OUT.exists():
        raise ValueError("Positive source probe already exists")
    scores, episodes = (json.loads(p.read_text()) for p in (SCORES, EPISODES))
    source_hash = digest(VIDEO)
    if (
        scores["source_video_sha256"] != source_hash
        or episodes["source_sha256"] != source_hash
        or episodes["right_tail_sha256"] != scores["input_sha256"]["scan"]
    ):
        raise ValueError("Score, episode or source lineage mismatch")
    selected = select(scores, episodes)
    by_id = {row["right_proposal_id"]: row for row in scores["rows"]}
    capture = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    fps = capture.get(cv2.CAP_PROP_FPS)
    if not capture.isOpened() or fps <= 0:
        raise ValueError("Czech video unreadable")
    OUT.mkdir(parents=True)
    rows = []
    try:
        for page_index, start in enumerate(range(0, len(selected), 3), 1):
            chunk = selected[start : start + 3]
            page = Image.new("RGB", (960, 504 * len(chunk)), "white")
            for row_index, (episode_id, pid, selection_kind) in enumerate(chunk):
                score = by_id[pid]
                for sample_index, sample in enumerate(score["samples"]):
                    time = sample["time_s"]
                    capture.set(cv2.CAP_PROP_POS_FRAMES, round(time * fps))
                    ok, frame = capture.read()
                    if not ok or frame.shape[:2] != (360, 640):
                        raise ValueError(f"Unreadable source sample: {pid} {time}")
                    panel = Image.fromarray(cv2.cvtColor(frame[:, 320:], cv2.COLOR_BGR2RGB))
                    draw = ImageDraw.Draw(panel)
                    x, y, w, h = sample["cap_bbox_px"]
                    draw.rectangle(
                        (x - 325, y - 5, x + w - 315, y + h + 5), outline="magenta", width=3
                    )
                    bx, by, side, _ = context_bbox(sample["cap_bbox_px"])
                    draw.rectangle(
                        (bx - 320, by, bx + side - 320, by + side), outline="cyan", width=2
                    )
                    draw.rectangle((0, 0, 260, 22), fill="white")
                    draw.text(
                        (3, 4),
                        f"{episode_id} {pid} {time:.0f}s score {sample['patch_score']:.2f}",
                        fill="black",
                    )
                    crop = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).crop(
                        (bx, by, bx + side, by + side)
                    )
                    crop = crop.resize((144, 144), Image.Resampling.NEAREST)
                    left, top = sample_index * 320, row_index * 504
                    page.paste(panel, (left, top))
                    page.paste(crop, (left + 88, top + 360))
                rows.append(
                    {
                        "episode_id": episode_id,
                        "right_proposal_id": pid,
                        "selection_kind": selection_kind,
                        "source_sample_times_s": [s["time_s"] for s in score["samples"]],
                        "positive_patch_count": score["positive_patch_count"],
                        "page": f"page-{page_index}.jpg",
                    }
                )
            page.save(OUT / f"page-{page_index}.jpg", quality=93)
    finally:
        capture.release()
    result = {
        "status": "fixed_postscore_positive_one_to_one_source_probe_not_event_truth",
        "source_video_sha256": source_hash,
        "input_sha256": {"scores": digest(SCORES), "episodes": digest(EPISODES)},
        "context_geometry_code_sha256": digest(ROOT / "prototype/cap_patch_verifier.py"),
        "runner_sha256": digest(Path(__file__)),
        "selection_rule": "12 evenly index-spaced among 90 positive one-to-one links plus 8 lowest mean-score remaining links",
        "rows": rows,
        "page_sha256": {p.name: digest(p) for p in sorted(OUT.glob("page-*.jpg"))},
        "limitations": [
            "Selected after model scores and temporal episode inventory existed; not an independent event benchmark.",
            "Three source-frame prefix samples cannot verify whole-track object or physical throw identity.",
            "Time-spaced and low-score sampling does not estimate full-inventory stone precision.",
        ],
    }
    (OUT / "manifest.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                "selected": len(rows),
                "pages": len(result["page_sha256"]),
                "time_spaced": sum(r["selection_kind"] == "time_spaced" for r in rows),
            }
        )
    )


if __name__ == "__main__":
    main()
