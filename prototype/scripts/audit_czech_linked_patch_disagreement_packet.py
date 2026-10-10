"""Record conservative source-pixel labels for Czech linked patch disagreements."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark/canada-czech-2024"
PACKET = BASE / "full-linked-right-patch-disagreement-source-packet"
OUT = BASE / "full-linked-right-patch-disagreement-pixel-audit.json"

STONE_ID = "R01:A029"
PERSON_EQUIPMENT_IDS = {
    "R01:A030", "R01:A034", "R01:A036", "R01:A114", "R01:A115",
    "R01:A118", "R01:A120", "R01:A184", "R01:A185", "R01:A247",
    "R01:A249", "R01:A250", "R01:A258", "R01:A259", "R01:A376",
}


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    manifest_path = PACKET / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    for name, expected in manifest["page_sha256"].items():
        if digest(PACKET / name) != expected:
            raise ValueError(f"Source page changed: {name}")
    for name, path in {
            "scores": BASE / "full-right-source-diverse-patch-transfer-development.json",
            "episodes": BASE / "full-corridor-right-episodes-first-transfer.json",
    }.items():
        if digest(path) != manifest["input_sha256"][name]:
            raise ValueError(f"Packet input changed: {name}")
    rows = manifest["rows"]
    ids = [row["right_proposal_id"] for row in rows]
    if (len(ids) != 16 or len(set(ids)) != 16 or
            set(ids) != PERSON_EQUIPMENT_IDS | {STONE_ID}):
        raise ValueError("Linked disagreement inventory changed")
    reviewed = [{**row,
                 "sampled_source_pixel_class": (
                     "moving_stone_pixels" if row["right_proposal_id"] == STONE_ID
                     else "person_or_equipment_pixels"),
                 "physical_throw_verified": False}
                for row in rows]
    counts = Counter((row["sampled_source_pixel_class"],
                      row["positive_patch_count"] > 0) for row in reviewed)
    if (counts["moving_stone_pixels", True] != 1 or
            counts["person_or_equipment_pixels", False] != 15):
        raise ValueError("Source class/patch score disagreement changed")
    result = {
        "status": "same_agent_postscore_linked_prefix_pixel_audit_not_event_truth",
        "manifest_sha256": digest(manifest_path),
        "source_video_sha256": manifest["source_video_sha256"],
        "page_sha256": manifest["page_sha256"],
        "sampled_stone_positive_count": 1,
        "sampled_person_equipment_negative_count": 15,
        "rows": reviewed,
        "limitations": [
            "Labels concern only highlighted prefix source pixels, not complete track identity or physical deliveries.",
            "Temporal left/right association does not verify the same physical stone.",
            "The packet was selected after scores and reviewed by the same agent; it is development evidence, not independent event accuracy.",
            "A person-track negative does not prove there was no other real stone in the same episode window.",
        ],
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"reviewed": len(reviewed), "stone_positive": 1,
                      "person_negative": 15}))


if __name__ == "__main__":
    main()
