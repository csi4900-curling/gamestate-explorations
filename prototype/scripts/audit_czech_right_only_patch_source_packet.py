"""Record source-pixel review of all Czech right-only patch-score prefixes."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark/canada-czech-2024"
PACKET = BASE / "full-right-only-source-diverse-review-packet"
OUT = BASE / "full-right-only-source-diverse-pixel-audit.json"

# Visual source-frame judgments of the highlighted boxes on all eight pages.
# This is not a whole-track or physical-event annotation.
PERSON_EQUIPMENT_IDS = {
    "R01:A023", "R01:A032", "R01:A035", "R01:A038", "R01:A077",
    "R01:A094", "R01:A099", "R01:A100", "R01:A101", "R01:A128",
    "R01:A181", "R01:A191", "R01:A224", "R01:A235", "R01:A236",
    "R01:A286", "R01:A287", "R01:A300", "R01:A349", "R01:A353",
    "R01:A363", "R01:A366", "R01:A367",
}


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    manifest_path = PACKET / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    for name, expected in manifest["page_sha256"].items():
        if digest(PACKET / name) != expected:
            raise ValueError(f"Source page changed: {name}")
    sources = {
        "scores": BASE / "full-right-source-diverse-patch-transfer-development.json",
        "episodes": BASE / "full-corridor-right-episodes-first-transfer.json",
    }
    for name, path in sources.items():
        if digest(path) != manifest["input_sha256"][name]:
            raise ValueError(f"Packet input changed: {name}")
    ids = [row["right_proposal_id"] for row in manifest["rows"]]
    if len(ids) != 23 or len(set(ids)) != 23 or set(ids) != PERSON_EQUIPMENT_IDS:
        raise ValueError("Right-only source review set changed")
    rows = [{**row, "sampled_source_pixel_class": "person_or_equipment_pixels",
             "physical_throw_verified": False}
            for row in manifest["rows"]]
    counts = Counter((row["sampled_source_pixel_class"],
                      row["positive_patch_count"] > 0) for row in rows)
    result = {
        "status": "same_agent_postscore_right_only_prefix_pixel_audit_not_event_truth",
        "manifest_sha256": digest(manifest_path),
        "source_video_sha256": manifest["source_video_sha256"],
        "page_sha256": manifest["page_sha256"],
        "sampled_person_or_equipment_count": 23,
        "positive_patch_person_or_equipment_count": counts[
            "person_or_equipment_pixels", True],
        "negative_patch_person_or_equipment_count": counts[
            "person_or_equipment_pixels", False],
        "rows": rows,
        "limitations": [
            "Only highlighted source-frame prefix samples were judged; this is not an exhaustive physical throw timeline.",
            "The reviewer saw the model results and the packet selection is right-only; the labels are same-agent postscore development evidence.",
            "All 23 sampled prefixes being people/equipment does not prove that a real stone was absent elsewhere in those time windows.",
            "The positive R01:A191 samples follow a player's Canada shirt, demonstrating one appearance false positive despite this model's strong negative scores on the other 22.",
        ],
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"reviewed": len(rows), "person_positive": result[
        "positive_patch_person_or_equipment_count"], "person_negative": result[
        "negative_patch_person_or_equipment_count"]}))


if __name__ == "__main__":
    main()
