"""Render Czech left-linked right paths that the frozen patch model scores weak."""

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
OUT = BASE / "full-linked-right-patch-disagreement-source-packet"


def digest(path):
    h = sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def main():
    if OUT.exists():
        raise ValueError("Linked patch disagreement packet already exists")
    scores, episodes = (json.loads(p.read_text()) for p in (SCORES, EPISODES))
    source_hash = digest(VIDEO)
    if (scores["source_video_sha256"] != source_hash or
            episodes["source_sha256"] != source_hash or
            episodes["right_tail_sha256"] != scores["input_sha256"]["scan"]):
        raise ValueError("Score, episode or source lineage mismatch")
    by_id = {r["right_proposal_id"]: r for r in scores["rows"]}
    selected = []
    for episode in episodes["episodes"]:
        if not episode["member_left_candidate_ids"]:
            continue
        for pid in episode["right_proposal_ids"]:
            score = by_id[pid]
            if (not score["any_positive_patch"] or
                    episode["episode_kind"] == "multiple_right_candidates"):
                selected.append((episode["episode_id"], episode[
                    "episode_kind"], pid))
    if len(selected) != 16 or len({pid for _, _, pid in selected}) != 16:
        raise ValueError("Linked disagreement inventory changed")
    selected.sort(key=lambda item: (by_id[item[2]]["passage_time_s"], item[2]))
    capture = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG,
                               [cv2.CAP_PROP_N_THREADS, 1])
    fps = capture.get(cv2.CAP_PROP_FPS)
    if not capture.isOpened() or fps <= 0:
        raise ValueError("Czech source unreadable")
    OUT.mkdir(parents=True)
    rows = []
    try:
        for page_index, start in enumerate(range(0, len(selected), 3), 1):
            chunk = selected[start:start + 3]
            page = Image.new("RGB", (960, 504 * len(chunk)), "white")
            for row_index, (episode_id, kind, pid) in enumerate(chunk):
                score = by_id[pid]
                for sample_index, sample in enumerate(score["samples"]):
                    time = sample["time_s"]
                    capture.set(cv2.CAP_PROP_POS_FRAMES, round(time * fps))
                    ok, frame = capture.read()
                    if not ok or frame.shape[:2] != (360, 640):
                        raise ValueError(f"Unreadable source sample: {pid} {time}")
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
                rows.append({"episode_id": episode_id,
                             "episode_kind": kind,
                             "right_proposal_id": pid,
                             "source_sample_times_s": [s["time_s"] for s in
                                                       score["samples"]],
                             "positive_patch_count": score[
                                 "positive_patch_count"],
                             "page": f"page-{page_index}.jpg"})
            page.save(OUT / f"page-{page_index}.jpg", quality=93)
    finally:
        capture.release()
    result = {
        "status": "fixed_left_linked_right_patch_disagreement_packet_not_event_truth",
        "source_video_sha256": source_hash,
        "input_sha256": {"scores": digest(SCORES), "episodes": digest(EPISODES)},
        "context_geometry_code_sha256": digest(ROOT / "prototype/cap_patch_verifier.py"),
        "runner_sha256": digest(Path(__file__)),
        "selection_rule": "All left-linked right proposals with zero positive patches, plus the other proposal in any multiple-right episode (16 total)",
        "rows": rows,
        "page_sha256": {p.name: digest(p) for p in sorted(OUT.glob("page-*.jpg"))},
        "limitations": [
            "Temporal left/right linkage does not prove physical stone identity.",
            "Three source-frame samples do not establish complete-track class or physical throw truth.",
            "This packet is selected after model scoring for same-agent development review.",
        ],
    }
    (OUT / "manifest.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"proposals": len(rows), "pages": len(result["page_sha256"])}))


if __name__ == "__main__":
    main()
