"""Preserve source-pixel review of all one-variant right-view queue groups."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark/canada-latvia-2024"
QUEUE = BASE / "full-right-variant-review-queue-development.json"
GAP_AUDIT = BASE / "full-right-gap2-novel-source-audit.json"
LATER_AUDIT = BASE / "full-right-global-later-episode-source-audit.json"
GLOBAL_PACKET = BASE / "full-right-global-singleton-source-packet/manifest.json"
OUT = BASE / "full-right-variant-singleton-source-audit.json"

# Visual inspection of the four new source pages. These are sampled-prefix
# pixel classes, not labels of complete physical tracks or throws.
GLOBAL_CLASSES = {
    "A083": "person_or_equipment_pixels_in_sampled_prefix",
    "A217": "person_or_equipment_pixels_in_sampled_prefix",
    "A497": "mixed_stone_person_or_equipment_pixels_identity_uncertain",
    "A530": "mixed_stone_person_or_equipment_pixels_identity_uncertain",
}


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def main():
    queue = json.loads(QUEUE.read_text())
    gap = json.loads(GAP_AUDIT.read_text())
    later = json.loads(LATER_AUDIT.read_text())
    packet = json.loads(GLOBAL_PACKET.read_text())
    if len({queue["source_video_sha256"], gap["source_video_sha256"],
            later["source_video_sha256"], packet["source_video_sha256"]}) != 1:
        raise ValueError("Source bytes differ")
    if packet["review_queue_sha256"] != digest(QUEUE):
        raise ValueError("Global packet does not match review queue")
    for page, expected in packet["page_sha256"].items():
        if digest(GLOBAL_PACKET.parent / page) != expected:
            raise ValueError("Global source page changed")
    gap_rows = {row["raw_track_id"]: row for row in gap["rows"]}
    later_rows = {row["raw_track_id"]: row for row in later["rows"]}
    global_rows = {row["raw_track_id"]: row for row in packet["rows"]}
    if set(global_rows) != set(GLOBAL_CLASSES):
        raise ValueError("Global reviewed proposal inventory changed")
    rows = []
    proposals = {row["proposal_id"]: row for row in queue["proposals"]}
    for group in queue["review_groups"]:
        names = {proposals[pid]["variant"] for pid in group["proposal_ids"]}
        if len(names) != 1:
            continue
        if len(group["proposal_ids"]) != 1:
            raise ValueError("Singleton-variant group has multiple proposals")
        pid = group["proposal_ids"][0]
        proposal = proposals[pid]
        track = proposal["raw_track_id"]
        if pid == "one_second_greedy:A046:1":
            if gap["old_without_temporal_counterpart"][0]["raw_track_id"] != track:
                raise ValueError("A046 prior source review missing")
            pixel_class = "person_or_equipment_pixels_in_sampled_prefix"
            evidence = "full-right-gap2-novel-source-audit.json:old_without_temporal_counterpart"
        elif proposal["variant"] == "two_second_greedy":
            source = gap_rows[track]
            if source["source_pixel_class"].startswith("person_or_equipment"):
                pixel_class = "person_or_equipment_pixels_in_sampled_prefix"
            else:
                pixel_class = "mixed_stone_person_or_equipment_pixels_identity_uncertain"
            evidence = source["source_page"]
        elif proposal["variant"] == "two_second_global_later":
            source = later_rows[track]
            if source["episode_index_within_raw_track"] != proposal[
                    "episode_index_within_raw_track"]:
                raise ValueError("Later episode identity changed")
            pixel_class = source["source_pixel_class"]
            evidence = source["review_page"]
        elif proposal["variant"] == "two_second_global":
            source = global_rows[track]
            if abs(source["passage_time_s"] - proposal["time_s"]) > 1e-6:
                raise ValueError("Global passage changed")
            pixel_class = GLOBAL_CLASSES[track]
            evidence = "full-right-global-singleton-source-packet/" + source["page"]
        else:
            raise ValueError(f"Unaudited singleton: {pid}")
        rows.append({"review_group_id": group["group_id"],
                     "proposal_id": pid,
                     "time_s": proposal["time_s"],
                     "source_pixel_class": pixel_class,
                     "source_evidence": evidence,
                     "physical_throw_verified": False})
    if len(rows) != 11:
        raise ValueError("Singleton inventory changed")
    counts = Counter(row["source_pixel_class"] for row in rows)
    if counts != {"person_or_equipment_pixels_in_sampled_prefix": 5,
                  "mixed_stone_person_or_equipment_pixels_identity_uncertain": 6}:
        raise ValueError("Source class inventory changed")
    result = {
        "status": "postproposal_singleton_source_pixel_review_not_throw_truth",
        "source_video_sha256": queue["source_video_sha256"],
        "input_sha256": {"queue": digest(QUEUE), "gap_source_audit": digest(GAP_AUDIT),
                         "later_source_audit": digest(LATER_AUDIT),
                         "global_source_packet_manifest": digest(GLOBAL_PACKET)},
        "runner_sha256": digest(Path(__file__)),
        "reviewed_singleton_group_count": len(rows),
        "source_class_counts": dict(counts),
        "rows": rows,
        "limitations": [
            "Source classes were assigned after proposals existed and are not independent physical throw labels.",
            "Mixed proposals may include moving stone pixels; single-variant support is not a safe automatic rejection rule.",
            "Three sampled source frames do not validate a complete track, throw, release or settle.",
            "This selected subset does not measure full-match detector precision, recall or F1.",
        ],
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"singletons": len(rows), "source_classes": dict(counts)}))


if __name__ == "__main__":
    main()
