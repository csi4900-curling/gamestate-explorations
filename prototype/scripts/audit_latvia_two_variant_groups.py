"""Join source-pixel classes for both members of two-variant review groups."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark/canada-latvia-2024"
QUEUE = BASE / "full-right-variant-review-queue-development.json"
PACKET = BASE / "full-right-two-variant-counterpart-source-packet/manifest.json"
GAP = BASE / "full-right-gap2-novel-source-audit.json"
LATER = BASE / "full-right-global-later-episode-source-audit.json"
OLDER = BASE / "remaining-right-only-source-audit/manifest.json"
OUT = BASE / "full-right-two-variant-source-audit.json"

# New visual review of three source samples for each previously unaudited
# member. A mixed label means the sampled pixels switch object or are unclear.
NEW_CLASSES = {
    "two_second_global:A184:1": "stone_pixels",
    "two_second_global:A315:1": "person_or_equipment_pixels",
    "two_second_global:A323:1": "stone_pixels",
    "two_second_global:A358:1": "person_or_equipment_pixels",
    "two_second_global:A391:1": "stone_pixels",
    "two_second_global:A399:1": "stone_pixels",
    "two_second_greedy:A425:1": "person_or_equipment_pixels",
    "two_second_global:A429:1": "person_or_equipment_pixels",
    "two_second_global:A434:1": "person_or_equipment_pixels",
    "two_second_global:A440:1": "mixed_or_identity_uncertain",
    "two_second_global:A484:1": "person_or_equipment_pixels",
}


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def normalized_class(source_class):
    if source_class.startswith(("moving_stone_body", "stone_pixels")):
        return "stone_pixels"
    if source_class.startswith(("person_or_equipment", "person_clothing")):
        return "person_or_equipment_pixels"
    if source_class.startswith("mixed"):
        return "mixed_or_identity_uncertain"
    raise ValueError(f"Unknown source class: {source_class}")


def main():
    queue = json.loads(QUEUE.read_text())
    packet = json.loads(PACKET.read_text())
    gap = json.loads(GAP.read_text())
    later = json.loads(LATER.read_text())
    older = json.loads(OLDER.read_text())
    if (
        packet["review_queue_sha256"] != digest(QUEUE)
        or len(
            {
                queue["source_video_sha256"],
                packet["source_video_sha256"],
                gap["source_video_sha256"],
                later["source_video_sha256"],
                older["source_video_sha256"],
            }
        )
        != 1
    ):
        raise ValueError("Source/queue lineage mismatch")
    for page, expected in packet["page_sha256"].items():
        if digest(PACKET.parent / page) != expected:
            raise ValueError("Counterpart source page changed")
    new_rows = {row["proposal_id"]: row for row in packet["rows"]}
    if set(new_rows) != set(NEW_CLASSES):
        raise ValueError("New source-review inventory changed")
    old_classes = {}
    for row in gap["rows"]:
        pid = f"two_second_greedy:{row['raw_track_id']}:1"
        old_classes[pid] = (normalized_class(row["source_pixel_class"]), row["source_page"])
    for row in later["rows"]:
        pid = (
            f"two_second_global_later:{row['raw_track_id']}:{row['episode_index_within_raw_track']}"
        )
        old_classes[pid] = (normalized_class(row["source_pixel_class"]), row["review_page"])
    old_a374 = next(row for row in older["rows"] if row["raw_track_id"] == "A374")
    if old_a374["source_sheet_sha256"] != digest(OLDER.parent / old_a374["source_sheet"]):
        raise ValueError("A374 source page changed")
    old_classes["one_second_greedy:A374:1"] = (
        normalized_class(old_a374["source_pixel_class"]),
        "remaining-right-only-source-audit/" + old_a374["source_sheet"],
    )

    rows = []
    for group in queue["review_groups"]:
        variants = {pid.split(":")[0] for pid in group["proposal_ids"]}
        if len(variants) != 2:
            continue
        members = []
        for pid in group["proposal_ids"]:
            if pid in NEW_CLASSES:
                source_class = NEW_CLASSES[pid]
                evidence = (
                    "full-right-two-variant-counterpart-source-packet/" + new_rows[pid]["page"]
                )
            else:
                source_class, evidence = old_classes[pid]
            members.append(
                {
                    "proposal_id": pid,
                    "source_pixel_class": source_class,
                    "source_evidence": evidence,
                    "physical_throw_verified": False,
                }
            )
        if len(members) != 2:
            raise ValueError("Unexpected two-variant group size")
        classes = sorted(member["source_pixel_class"] for member in members)
        rows.append(
            {
                "review_group_id": group["group_id"],
                "source_class_pair": classes,
                "members": members,
                "physical_throw_verified": False,
            }
        )
    if len(rows) != 11 or {
        member["proposal_id"]
        for row in rows
        for member in row["members"]
        if member["proposal_id"] in NEW_CLASSES
    } != set(NEW_CLASSES):
        raise ValueError("Two-variant audit inventory changed")
    counts = Counter(" + ".join(row["source_class_pair"]) for row in rows)
    expected = {
        "stone_pixels + stone_pixels": 3,
        "mixed_or_identity_uncertain + stone_pixels": 1,
        "person_or_equipment_pixels + person_or_equipment_pixels": 4,
        "mixed_or_identity_uncertain + person_or_equipment_pixels": 2,
        "mixed_or_identity_uncertain + mixed_or_identity_uncertain": 1,
    }
    if counts != expected:
        raise ValueError(f"Two-variant source-class inventory changed: {counts}")
    result = {
        "status": "postproposal_two_variant_source_pixel_review_not_throw_truth",
        "source_video_sha256": queue["source_video_sha256"],
        "input_sha256": {
            "queue": digest(QUEUE),
            "counterpart_source_packet": digest(PACKET),
            "gap_source_audit": digest(GAP),
            "later_source_audit": digest(LATER),
            "older_right_source_audit": digest(OLDER),
        },
        "runner_sha256": digest(Path(__file__)),
        "reviewed_group_count": len(rows),
        "source_class_pair_counts": dict(counts),
        "rows": rows,
        "limitations": [
            "Source-pixel classes are postproposal review, not independent physical throw labels.",
            "Two-variant agreement can be stone pixels or person/equipment pixels; it is not a physical-event classifier.",
            "A stone-pixel prefix does not establish complete same-stone trajectory, release or settle.",
            "These selected groups do not measure full-match precision, recall or F1.",
        ],
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"groups": len(rows), "class_pairs": dict(counts)}))


if __name__ == "__main__":
    main()
