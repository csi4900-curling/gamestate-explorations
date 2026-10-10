"""Preserve source classes and A452 tail evidence for four later global spans."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark/canada-latvia-2024"
VIDEO = BASE / "source-360p.mp4"
PROBE = BASE / "full-right-global-multi-episode-development.json"
PACKET = BASE / "full-right-global-later-episode-source-packet/manifest.json"
BASELINE = BASE / "full-right-area-first-transfer.json"
GLOBAL = BASE / "full-right-global-area-development.json"
OUT = BASE / "full-right-global-later-episode-source-audit.json"


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def main():
    if OUT.exists():
        raise ValueError("Later-episode source audit already exists")
    probe, packet, baseline, global_scan = [json.loads(path.read_text())
        for path in (PROBE, PACKET, BASELINE, GLOBAL)]
    source_hash = digest(VIDEO)
    if (not probe["source_sha256"] == packet["source_video_sha256"] ==
            baseline["source_sha256"] == global_scan["source_sha256"] ==
            source_hash or packet["multi_episode_probe_sha256"] != digest(PROBE) or
            packet["runner_sha256"] != digest(
                ROOT / "prototype/scripts/render_latvia_global_later_episodes.py") or
            any(page["sha256"] != digest(PACKET.parent / page["image"])
                for page in packet["pages"])):
        raise ValueError("Later-episode packet/source lineage differs")
    ids = {row["raw_track_id"] for row in packet["rows"]}
    if len(packet["rows"]) != 4 or ids != {"A006", "A269", "A420", "A530"}:
        raise ValueError("Later-episode source review inventory differs")
    rows = []
    for row in packet["rows"]:
        track_id = row["raw_track_id"]
        pixel_class = ("stone_pixels_with_later_moving_tail_identity_uncertain"
                       if track_id == "A530" else
                       "mixed_stone_person_or_equipment_pixels_identity_uncertain")
        rows.append({
            "raw_track_id": track_id,
            "episode_index_within_raw_track": row[
                "episode_index_within_raw_track"],
            "source_time_s": row["passage_time_s"],
            "source_pixel_class": pixel_class,
            "class_origin": "same_agent_postproposal_three_source_frame_review",
            "review_page": "full-right-global-later-episode-source-packet/" + row[
                "review_page"],
            "physical_throw_verified": False,
        })
    counts = Counter(row["source_pixel_class"] for row in rows)
    if counts != {"mixed_stone_person_or_equipment_pixels_identity_uncertain": 3,
                  "stone_pixels_with_later_moving_tail_identity_uncertain": 1}:
        raise ValueError("Later-episode pixel class counts differ")
    a452 = next(row for row in baseline["raw_tracks"] if row["track_id"] == "A452")
    a530 = next(row for row in global_scan["raw_tracks"] if row[
        "track_id"] == "A530")
    baseline_tail = [point for point in a452["points"] if 6400 <= point[
        "time_s"] <= 6407]
    global_tail = [point for point in a530["points"] if 6400 <= point[
        "time_s"] <= 6407]
    later = next(row for row in probe["later_review_proposals"] if row[
        "raw_track_id"] == "A530")
    if (len(baseline_tail) != 8 or baseline_tail != global_tail or
            later["episode_index_within_raw_track"] != 2 or
            not 6403 <= later["passage"]["time_s"] <= 6405 or
            later["direction"] != "positive_y"):
        raise ValueError("A452/A530 late stone tail correspondence differs")
    output = {
        "status": "postinspection_later_global_source_pixel_review_not_throw_truth",
        "source_video_sha256": source_hash,
        "input_sha256": {
            "multi_episode_probe": digest(PROBE),
            "source_packet_manifest": digest(PACKET),
            "one_second_area_scan": digest(BASELINE),
            "global_area_scan": digest(GLOBAL),
        },
        "runner_sha256": digest(Path(__file__)),
        "source_class_counts": dict(counts),
        "baseline_A452_global_A530_tail_interval_s": [6400, 6407],
        "baseline_A452_global_A530_tail_observations_equal": True,
        "A530_later_passage_time_s": later["passage"]["time_s"],
        "rows": rows,
        "limitations": [
            "Source-pixel classes were assigned after the new proposal extractor and are not independent physical throw labels.",
            "A530 contains the same eight late image observations as baseline A452, but long-track physical identity before them is unresolved.",
            "Three other later proposals switch among stone, person or equipment pixels and are unsafe as automatic events.",
            "Restoring a source-visible timing cue does not validate full-match throw F1 or simulation state.",
        ],
    }
    OUT.write_text(json.dumps(output, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"later_source_classes": dict(counts),
                      "A452_timing_restored_at_s": later["passage"]["time_s"]}))


if __name__ == "__main__":
    main()
