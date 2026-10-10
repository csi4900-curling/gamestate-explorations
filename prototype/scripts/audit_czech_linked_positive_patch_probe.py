"""Record source-pixel classes for the fixed Czech positive one-to-one probe."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark/canada-czech-2024"
PACKET = BASE / "full-linked-positive-patch-source-probe"
OUT = BASE / "full-linked-positive-patch-pixel-audit.json"

STONE_IDS = {
    "R01:A001",
    "R01:A014",
    "R01:A025",
    "R01:A046",
    "R01:A060",
    "R01:A072",
    "R01:A136",
    "R01:A154",
    "R01:A159",
    "R01:A183",
    "R01:A200",
    "R01:A203",
    "R01:A213",
    "R01:A223",
    "R01:A228",
    "R01:A246",
    "R01:A269",
    "R01:A289",
    "R01:A318",
    "R01:A358",
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
    ids = [row["right_proposal_id"] for row in manifest["rows"]]
    if len(ids) != 20 or len(set(ids)) != 20 or set(ids) != STONE_IDS:
        raise ValueError("Positive probe inventory changed")
    selection_counts = Counter(row["selection_kind"] for row in manifest["rows"])
    if selection_counts != {"time_spaced": 12, "lowest_mean_score_remaining": 8}:
        raise ValueError("Positive probe selection changed")
    rows = [
        {
            **row,
            "sampled_source_pixel_class": "moving_stone_pixels",
            "physical_throw_verified": False,
        }
        for row in manifest["rows"]
    ]
    result = {
        "status": "same_agent_postscore_positive_prefix_pixel_audit_not_event_truth",
        "manifest_sha256": digest(manifest_path),
        "source_video_sha256": manifest["source_video_sha256"],
        "page_sha256": manifest["page_sha256"],
        "reviewed_positive_one_to_one_prefix_count": len(rows),
        "sampled_moving_stone_pixel_count": len(rows),
        "selection_counts": dict(selection_counts),
        "rows": rows,
        "limitations": [
            "The sample was selected after scores: 12 time-spaced plus eight least-confident remaining positives. It cannot estimate precision on all 90 positive one-to-one proposals.",
            "Only three highlighted frames of each prefix were reviewed, not complete tracks or independently labelled physical deliveries.",
            "A stone-pixel prefix and a temporal camera link do not verify physical stone identity, release, settle or event recall.",
            "This is same-agent development evidence, not an independent full-match F1 benchmark.",
        ],
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                "reviewed": len(rows),
                "moving_stone_pixels": len(rows),
                "selection": dict(selection_counts),
            }
        )
    )


if __name__ == "__main__":
    main()
