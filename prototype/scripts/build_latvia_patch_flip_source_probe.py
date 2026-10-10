"""Render fixed source frames for unreviewed new-model patch flips."""

from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cap_patch_verifier import context_bbox

BASE = ROOT / "validation/throw-event-benchmark/canada-latvia-2024"
VIDEO = BASE / "source-360p.mp4"
QUEUE = BASE / "full-right-variant-review-queue-development.json"
SCORES = BASE / "full-right-all-proposal-source-diverse-patch-development.json"
REVIEWED = ROOT / "validation/throw-event-benchmark/right-sideview-source-diverse-development-v1/latvia-fixed-source-review-transfer.json"
SCANS = {
    "one_second_greedy": BASE / "full-right-area-first-transfer.json",
    "two_second_greedy": BASE / "full-right-area-gap2-development.json",
    "two_second_global": BASE / "full-right-global-area-development.json",
    "two_second_global_later": BASE / "full-right-global-multi-episode-development.json",
}
OUT = BASE / "full-right-patch-flip-source-probe"


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def select(queue, scores, reviewed):
    by_id = {row["proposal_id"]: row for row in scores["proposals"]}
    known = {row["proposal_id"] for row in reviewed["rows"]}
    losses = [row for row in scores["proposals"] if row["proposal_id"] not in known
              and row["old_model_any_positive_patch"]
              and not row["new_model_any_positive_patch"]]
    if len(losses) != 5:
        raise ValueError("Unreviewed lost-proposal inventory changed")
    eligible_groups = []
    for group in queue["review_groups"]:
        ids = group["proposal_ids"]
        if set(ids) & known:
            continue
        gains = [pid for pid in ids if not by_id[pid][
            "old_model_any_positive_patch"] and by_id[pid][
                "new_model_any_positive_patch"]]
        if gains:
            eligible_groups.append((group, gains))
    if len(eligible_groups) != 43:
        raise ValueError("Unreviewed gained-group inventory changed")
    selected = []
    for index in range(15):
        group, gains = eligible_groups[round(index * (len(eligible_groups) - 1)
                                               / 14)]
        pid = min(gains, key=lambda value: (by_id[value][
            "sample_patch_scores"][1]["time_s"], value))
        selected.append({"selection_kind": "new_positive_time_spaced_group",
                         "review_group_id": group["group_id"],
                         "proposal_id": pid})
    for row in losses:
        selected.append({"selection_kind": "all_new_negative_old_positive_unreviewed",
                         "review_group_id": row["review_group_id"],
                         "proposal_id": row["proposal_id"]})
    if len(selected) != 20 or len({row["proposal_id"] for row in selected}) != 20:
        raise ValueError("Patch-flip selection duplicates proposal")
    return sorted(selected, key=lambda row: (by_id[row["proposal_id"]][
        "sample_patch_scores"][1]["time_s"], row["proposal_id"]))


def main():
    if OUT.exists():
        raise ValueError("Patch-flip source packet exists")
    queue, scores, reviewed = (json.loads(path.read_text()) for path in (
        QUEUE, SCORES, REVIEWED))
    video_hash = digest(VIDEO)
    if (queue["source_video_sha256"] != video_hash or
            scores["source_video_sha256"] != video_hash or
            scores["input_sha256"]["queue"] != digest(QUEUE) or
            scores["input_sha256"]["reviewed_new_model_transfer"] !=
            digest(REVIEWED)):
        raise ValueError("Queue, score or video lineage mismatch")
    chosen = select(queue, scores, reviewed)
    by_score = {row["proposal_id"]: row for row in scores["proposals"]}
    proposals = {}
    raw_tracks = {}
    for name, path in SCANS.items():
        scan = json.loads(path.read_text())
        if queue["input_sha256"][name] != digest(path):
            raise ValueError("Scan changed")
        entries = (scan["later_review_proposals"] if name.endswith("_later")
                   else scan["directional_review_proposals"])
        for proposal in entries:
            pid = (f"{name}:{proposal['raw_track_id']}:"
                   f"{proposal.get('episode_index_within_raw_track', 1)}")
            proposals[pid] = proposal
        if "raw_tracks" in scan:
            raw_tracks[name] = {row["track_id"]: row for row in scan["raw_tracks"]}
    raw_tracks["two_second_global_later"] = raw_tracks["two_second_global"]
    capture = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG,
                               [cv2.CAP_PROP_N_THREADS, 1])
    fps = capture.get(cv2.CAP_PROP_FPS)
    if not capture.isOpened() or fps <= 0:
        raise ValueError("Video unreadable")
    OUT.mkdir(parents=True)
    rows = []
    try:
        for page_index, start in enumerate(range(0, len(chosen), 3), 1):
            chunk = chosen[start:start + 3]
            sheet = Image.new("RGB", (960, 504 * len(chunk)), "white")
            for row_index, item in enumerate(chunk):
                pid = item["proposal_id"]
                variant, track, _ = pid.split(":")
                proposal = proposals[pid]
                points = proposal["observed_prefix_points"]
                if len(points) < 3:
                    points = raw_tracks[variant][track]["points"]
                by_time = {point["time_s"]: point for point in points}
                score = by_score[pid]
                sample_times = [sample["time_s"] for sample in score[
                    "sample_patch_scores"]]
                if not all(time in by_time for time in sample_times):
                    raise ValueError("Score sample absent from track")
                for sample_index, time in enumerate(sample_times):
                    capture.set(cv2.CAP_PROP_POS_FRAMES, round(time * fps))
                    ok, frame = capture.read()
                    if not ok or frame.shape[:2] != (360, 640):
                        raise ValueError("Source frame unreadable")
                    point = by_time[time]
                    panel = Image.fromarray(cv2.cvtColor(frame[:, 320:],
                                                         cv2.COLOR_BGR2RGB))
                    draw = ImageDraw.Draw(panel)
                    x, y, w, h = point["bbox"]
                    draw.rectangle((x - 325, y - 5, x - 315 + w, y + h + 5),
                                   outline="magenta", width=3)
                    bx, by, side, _ = context_bbox(point["bbox"])
                    draw.rectangle((bx - 320, by, bx + side - 320, by + side),
                                   outline="cyan", width=2)
                    draw.rectangle((0, 0, 220, 22), fill="white")
                    draw.text((3, 4), f"{item['review_group_id']} {track} {time:.0f}s",
                              fill="black")
                    source = Image.fromarray(cv2.cvtColor(frame,
                                                           cv2.COLOR_BGR2RGB))
                    crop = source.crop((bx, by, bx + side, by + side))
                    crop = crop.resize((144, 144), Image.Resampling.NEAREST)
                    left, top = sample_index * 320, row_index * 504
                    sheet.paste(panel, (left, top))
                    sheet.paste(crop, (left + 88, top + 360))
                rows.append({**item,
                             "source_sample_times_s": sample_times,
                             "old_model_any_positive_patch": score[
                                 "old_model_any_positive_patch"],
                             "new_model_any_positive_patch": score[
                                 "new_model_any_positive_patch"],
                             "source_page": f"page-{page_index}.jpg"})
            sheet.save(OUT / f"page-{page_index}.jpg", quality=93)
    finally:
        capture.release()
    result = {
        "status": "postscore_fixed_patch_flip_source_probe_not_event_truth",
        "source_video_sha256": video_hash,
        "input_sha256": {"queue": digest(QUEUE), "scores": digest(SCORES),
                         "reviewed_transfer": digest(REVIEWED),
                         **{name: digest(path) for name, path in SCANS.items()}},
        "context_geometry_code_sha256": digest(ROOT / "prototype/cap_patch_verifier.py"),
        "runner_sha256": digest(Path(__file__)),
        "selection_rule": "All five old-positive/new-negative unreviewed proposal prefixes plus one earliest eligible new-only proposal from each of 15 evenly time-spaced groups with no previously reviewed member",
        "rows": rows,
        "page_sha256": {path.name: digest(path) for path in OUT.glob("page-*.jpg")},
        "limitations": [
            "One gain proposal per selected group and three source frames cannot classify other group members or the complete track.",
            "Time-spaced groups were selected after model scores existed; source-pixel review will not be independent event truth.",
            "A stone-like patch may depict handling or displacement rather than a new delivery.",
        ],
    }
    (OUT / "manifest.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"proposals": len(rows),
                      "gains": sum(r["selection_kind"].startswith("new_positive")
                                   for r in rows),
                      "losses": sum(r["selection_kind"].startswith("all_new_negative")
                                    for r in rows),
                      "pages": len(result["page_sha256"])}))


if __name__ == "__main__":
    main()
