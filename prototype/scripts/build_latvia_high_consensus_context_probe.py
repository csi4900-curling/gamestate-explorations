"""Render fixed high-consensus clear/cluttered source samples for cue audit."""

from hashlib import sha256
import json
from pathlib import Path

import cv2
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark/canada-latvia-2024"
VIDEO = BASE / "source-360p.mp4"
QUEUE = BASE / "full-right-variant-review-queue-development.json"
SCORES = BASE / "full-right-all-proposal-context-review-development.json"
SCANS = {
    "one_second_greedy": BASE / "full-right-area-first-transfer.json",
    "two_second_greedy": BASE / "full-right-area-gap2-development.json",
    "two_second_global": BASE / "full-right-global-area-development.json",
    "two_second_global_later": BASE / "full-right-global-multi-episode-development.json",
}
OUT = BASE / "full-right-high-consensus-context-source-probe"


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def select_groups(queue, scores):
    score_groups = {g["review_group_id"]: g for g in scores["review_groups"]}
    proposal_scores = {r["proposal_id"]: r for r in scores["proposals"]}
    high = [g for g in queue["review_groups"] if len({
        pid.split(":")[0] for pid in g["proposal_ids"]}) == 3]
    clear = [g for g in high if score_groups[g["group_id"]][
        "context_review_priority"] == "has_clear_context_proposal"]
    cluttered = [g for g in high if score_groups[g["group_id"]][
        "context_review_priority"] == "all_proposals_context_cluttered_review"]
    if len(clear) != 86 or len(cluttered) != 10:
        raise ValueError("High-consensus context inventory changed")
    # Every cluttered group; ten clear groups evenly spaced in passage-time order.
    chosen_clear = [clear[round(index * (len(clear) - 1) / 9)]
                    for index in range(10)]
    result = []
    for group in sorted(cluttered + chosen_clear,
                        key=lambda g: (g["first_time_s"], g["group_id"])):
        priority = score_groups[group["group_id"]]["context_review_priority"]
        ids = group["proposal_ids"]
        if priority == "has_clear_context_proposal":
            ids = [pid for pid in ids if proposal_scores[pid][
                "frozen_paired_context_tier"] == "clear_context_review"]
        pid = min(ids, key=lambda key: (proposal_scores[key]["passage_time_s"], key))
        result.append((group, pid, priority))
    return result


def main():
    queue = json.loads(QUEUE.read_text())
    scores = json.loads(SCORES.read_text())
    scans = {name: json.loads(path.read_text()) for name, path in SCANS.items()}
    video_hash = digest(VIDEO)
    if (queue["source_video_sha256"] != video_hash or
            scores["source_video_sha256"] != video_hash or
            scores["input_sha256"]["queue"] != digest(QUEUE) or
            any(queue["input_sha256"][name] != digest(path) for name, path in
                SCANS.items())):
        raise ValueError("Source/queue/score lineage mismatch")
    chosen = select_groups(queue, scores)
    proposal_rows = {}
    raw_tracks = {}
    for name, scan in scans.items():
        entries = (scan["later_review_proposals"] if name.endswith("_later")
                   else scan["directional_review_proposals"])
        for row in entries:
            pid = (f"{name}:{row['raw_track_id']}:"
                   f"{row.get('episode_index_within_raw_track', 1)}")
            proposal_rows[pid] = row
        if "raw_tracks" in scan:
            raw_tracks[name] = {r["track_id"]: r for r in scan["raw_tracks"]}
    raw_tracks["two_second_global_later"] = raw_tracks["two_second_global"]
    if OUT.exists():
        raise ValueError("Source probe exists")
    capture = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG,
                               [cv2.CAP_PROP_N_THREADS, 1])
    fps = capture.get(cv2.CAP_PROP_FPS)
    if not capture.isOpened() or fps <= 0:
        raise ValueError("Source unreadable")
    OUT.mkdir(parents=True)
    rows = []
    try:
        for page_index, start in enumerate(range(0, len(chosen), 3), 1):
            chunk = chosen[start:start + 3]
            sheet = Image.new("RGB", (960, 504 * len(chunk)), "white")
            for row_index, (group, pid, priority) in enumerate(chunk):
                proposal = proposal_rows[pid]
                variant, track, _ = pid.split(":")
                points = proposal["observed_prefix_points"]
                if len(points) < 3:
                    points = raw_tracks[variant][track]["points"]
                    sampling_policy = "nearest_three_raw_track_points"
                else:
                    sampling_policy = "nearest_three_prefix_points"
                time = proposal["passage"]["time_s"]
                samples = sorted(sorted(points, key=lambda p: (
                    abs(p["time_s"] - time), p["time_s"]))[:3],
                                 key=lambda p: p["time_s"])
                if len(samples) != 3:
                    raise ValueError(f"Too few source points: {pid}")
                for sample_index, point in enumerate(samples):
                    capture.set(cv2.CAP_PROP_POS_FRAMES,
                                round(point["time_s"] * fps))
                    ok, frame = capture.read()
                    if not ok or frame.shape[:2] != (360, 640):
                        raise ValueError("Source frame unreadable")
                    panel = Image.fromarray(cv2.cvtColor(frame[:, 320:],
                                                         cv2.COLOR_BGR2RGB))
                    draw = ImageDraw.Draw(panel)
                    x, y, w, h = point["bbox"]
                    draw.rectangle((x - 325, y - 5, x - 315 + w, y + h + 5),
                                   outline="magenta", width=3)
                    draw.rectangle((0, 0, 210, 22), fill="white")
                    draw.text((3, 4), f"{group['group_id']} {track} {point['time_s']:.0f}s",
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
                rows.append({"review_group_id": group["group_id"],
                             "proposal_id": pid,
                             "context_review_priority": priority,
                             "passage_time_s": time,
                             "sample_times_s": [p["time_s"] for p in samples],
                             "sampling_policy": sampling_policy,
                             "page": f"page-{page_index}.jpg"})
            sheet.save(OUT / f"page-{page_index}.jpg", quality=93)
    finally:
        capture.release()
    manifest = {
        "status": "postscore_fixed_high_consensus_source_probe_not_event_truth",
        "source_video_sha256": video_hash,
        "review_queue_sha256": digest(QUEUE),
        "full_context_score_sha256": digest(SCORES),
        "scan_sha256": {name: digest(path) for name, path in SCANS.items()},
        "runner_sha256": digest(Path(__file__)),
        "selection": "All 10 three-variant all-cluttered groups plus 10 clear three-variant groups evenly spaced in passage-time order; earliest eligible proposal per group",
        "rows": rows,
        "page_sha256": {p.name: digest(p) for p in OUT.glob("page-*.jpg")},
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"rows": len(rows), "pages": len(manifest["page_sha256"])}))


if __name__ == "__main__":
    main()
