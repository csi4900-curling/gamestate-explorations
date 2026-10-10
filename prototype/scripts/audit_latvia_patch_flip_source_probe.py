"""Record conservative source-pixel judgments for the fixed patch-flip packet."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark/canada-latvia-2024"
PACKET = BASE / "full-right-patch-flip-source-probe"
OUTPUT = BASE / "full-right-patch-flip-source-audit.json"

# These are visual judgments of the three highlighted source-frame boxes only.
# They do not say whether a newly delivered stone or complete throw exists.
JUDGMENTS = {
    "one_second_greedy:A006:1": "moving_stone_pixels",
    "one_second_greedy:A013:1": "moving_stone_pixels",
    "one_second_greedy:A018:1": "moving_stone_pixels",
    "one_second_greedy:A026:1": "moving_stone_pixels",
    "one_second_greedy:A036:1": "moving_stone_pixels",
    "two_second_global_later:A006:2": "mixed_stone_and_person_pixels",
    "one_second_greedy:A104:1": "moving_stone_pixels",
    "one_second_greedy:A147:1": "moving_stone_pixels",
    "one_second_greedy:A158:1": "moving_stone_pixels",
    "one_second_greedy:A181:1": "moving_stone_pixels",
    "one_second_greedy:A231:1": "moving_stone_pixels",
    "one_second_greedy:A304:1": "moving_stone_pixels",
    "two_second_greedy:A369:1": "person_or_equipment_pixels",
    "one_second_greedy:A342:1": "moving_stone_pixels",
    "one_second_greedy:A356:1": "moving_stone_pixels",
    "one_second_greedy:A364:1": "moving_stone_pixels",
    "two_second_global:A492:1": "person_or_equipment_pixels",
    "two_second_global:A500:1": "person_or_equipment_pixels",
    "two_second_greedy:A493:1": "person_or_equipment_pixels",
    "one_second_greedy:A452:1": "moving_stone_pixels",
}


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    manifest_path = PACKET / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    for name, expected in manifest["page_sha256"].items():
        if digest(PACKET / name) != expected:
            raise ValueError(f"Source page changed: {name}")
    for name, expected in manifest["input_sha256"].items():
        path = (
            BASE / "full-right-variant-review-queue-development.json"
            if name == "queue"
            else BASE / "full-right-all-proposal-source-diverse-patch-development.json"
            if name == "scores"
            else ROOT
            / "validation/throw-event-benchmark/right-sideview-source-diverse-development-v1/latvia-fixed-source-review-transfer.json"
            if name == "reviewed_transfer"
            else BASE
            / {
                "one_second_greedy": "full-right-area-first-transfer.json",
                "two_second_greedy": "full-right-area-gap2-development.json",
                "two_second_global": "full-right-global-area-development.json",
                "two_second_global_later": "full-right-global-multi-episode-development.json",
            }[name]
        )
        if digest(path) != expected:
            raise ValueError(f"Input changed: {name}")
    rows = manifest["rows"]
    ids = [row["proposal_id"] for row in rows]
    if len(rows) != 20 or len(set(ids)) != 20 or set(ids) != set(JUDGMENTS):
        raise ValueError("Fixed source packet changed")
    reviewed = [{**row, "source_pixel_judgment": JUDGMENTS[row["proposal_id"]]} for row in rows]
    counts = {
        kind: dict(
            Counter(
                row["source_pixel_judgment"] for row in reviewed if row["selection_kind"] == kind
            )
        )
        for kind in sorted({row["selection_kind"] for row in reviewed})
    }
    result = {
        "status": "same_agent_postscore_three_frame_source_pixel_audit_not_event_truth",
        "manifest_sha256": digest(manifest_path),
        "source_video_sha256": manifest["source_video_sha256"],
        "page_sha256": manifest["page_sha256"],
        "counts_by_selection_kind": counts,
        "rows": reviewed,
        "limitations": [
            "The reviewer saw old and new model scores when selecting this packet; this is not independent validation.",
            "Only three highlighted source frames per proposal were reviewed, not complete tracks or all proposals in each group.",
            "Moving stone pixels do not prove a newly delivered stone, physical event identity, or complete throw segmentation.",
            "The mixed loss has stone pixels in early samples and person pixels in the final sample; it must not be counted as a clean stone miss or clean false positive.",
            "Unreviewed proposals and physical event recall remain unknown.",
        ],
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(counts, sort_keys=True))


if __name__ == "__main__":
    main()
