"""Preserve source-pixel classes for all novel full-match gap-two proposals."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark/canada-latvia-2024"
PACKET = BASE / "full-right-gap2-novel-source-packet/manifest.json"
OLD = BASE / "full-right-area-first-transfer.json"
NEW = BASE / "full-right-area-gap2-development.json"
VIDEO = BASE / "source-360p.mp4"
OUT = BASE / "full-right-gap2-novel-source-audit.json"

STONE_IDS = {"A176", "A388", "A398"}
PERSON_IDS = {"A046", "A156", "A303", "A353", "A431", "A553"}
MIXED_IDS = {"A244", "A282", "A312", "A437", "A481", "A518"}


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def main():
    if OUT.exists():
        raise ValueError("Gap-two source audit already exists")
    packet = json.loads(PACKET.read_text())
    old = json.loads(OLD.read_text())
    new = json.loads(NEW.read_text())
    if not packet["source_video_sha256"] == old["source_sha256"] == new[
            "source_sha256"] == digest(VIDEO):
        raise ValueError("Novel packet/source video differs")
    if (packet["one_second_gap_scan_sha256"] != digest(OLD) or
            packet["two_second_gap_scan_sha256"] != digest(NEW) or
            packet["runner_sha256"] != digest(
                ROOT / "prototype/scripts/build_latvia_gap2_novel_source_packet.py") or
            any(page["sha256"] != digest(PACKET.parent / page["image"])
                for page in packet["pages"])):
        raise ValueError("Novel source packet lineage differs")
    ids = {row["raw_track_id"] for row in packet["rows"]}
    if (len(packet["rows"]) != 15 or len(ids) != 15 or
            ids != STONE_IDS | PERSON_IDS | MIXED_IDS or
            STONE_IDS & PERSON_IDS or STONE_IDS & MIXED_IDS or
            PERSON_IDS & MIXED_IDS):
        raise ValueError("Novel source class inventory differs")
    rows = []
    for row in packet["rows"]:
        track_id = row["raw_track_id"]
        if track_id in STONE_IDS:
            pixel_class = "moving_stone_body_pixels_in_prefix_samples"
        elif track_id in PERSON_IDS:
            pixel_class = "person_or_equipment_pixels_in_prefix_samples"
        else:
            pixel_class = "mixed_object_pixels_or_identity_uncertain"
        rows.append({
            "raw_track_id": track_id,
            "source_time_s": row["passage_time_s"],
            "colour_claim": row["colour_claim"],
            "direction": row["direction"],
            "source_pixel_class": pixel_class,
            "class_origin": "same_agent_postscore_three_source_frame_review",
            "source_page": "full-right-gap2-novel-source-packet/" + row[
                "review_page"],
            "sampling_policy": row["sampling_policy"],
            "physical_throw_verified": False,
        })
    counts = Counter(row["source_pixel_class"] for row in rows)
    if counts != {"moving_stone_body_pixels_in_prefix_samples": 3,
                  "person_or_equipment_pixels_in_prefix_samples": 6,
                  "mixed_object_pixels_or_identity_uncertain": 6}:
        raise ValueError("Novel source review counts differ")
    old_without_counterpart = [row for row in old["directional_review_proposals"]
        if not any(other["colour_claim"] == row["colour_claim"] and
                   other["direction"] == row["direction"] and
                   abs(other["passage"]["time_s"] - row["passage"]["time_s"]) <= 8
                   for other in new["directional_review_proposals"])]
    if len(old_without_counterpart) != 1 or old_without_counterpart[0][
            "raw_track_id"] != "A046":
        raise ValueError("Old proposal disappearance inventory differs")
    output = {
        "status": "postscore_novel_gap2_source_pixel_review_not_throw_truth",
        "source_video_sha256": digest(VIDEO),
        "one_second_gap_scan_sha256": digest(OLD),
        "two_second_gap_scan_sha256": digest(NEW),
        "source_packet_manifest_sha256": digest(PACKET),
        "runner_sha256": digest(Path(__file__)),
        "comparison_rule": packet["novelty_rule"],
        "one_second_gap_raw_track_count": old["raw_track_count"],
        "two_second_gap_raw_track_count": new["raw_track_count"],
        "one_second_gap_proposal_count": old["directional_proposal_count"],
        "two_second_gap_proposal_count": new["directional_proposal_count"],
        "new_without_temporal_counterpart_count": len(rows),
        "source_class_counts": dict(counts),
        "old_without_temporal_counterpart": [{
            "raw_track_id": row["raw_track_id"],
            "source_time_s": row["passage"]["time_s"],
            "colour_claim": row["colour_claim"],
            "direction": row["direction"],
            "prior_source_review": "person_or_clothing_pixels_in_withheld_cross_view_audit",
        } for row in old_without_counterpart],
        "rows": rows,
        "limitations": [
            "Same-agent source classes were assigned after the full gap-two scan and do not supply independent physical throw labels.",
            "Temporal comparison uses colour, direction and an eight-second window, not verified same-stone identity.",
            "Mixed long paths can splice a stone to a person or another object; a source-visible stone in one frame does not validate the track.",
            "The old A046 proposal that lacks a counterpart was previously source-reviewed on person/clothing pixels.",
            "Neither gross proposal count nor this selected novel subset measures full-match precision, recall or F1.",
        ],
    }
    OUT.write_text(json.dumps(output, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"new_without_temporal_counterpart": len(rows),
                      "source_classes": dict(counts),
                      "old_without_counterpart": "A046"}))


if __name__ == "__main__":
    main()
