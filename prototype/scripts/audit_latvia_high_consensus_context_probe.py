"""Record source-pixel classes for the frozen high-consensus context probe."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark/canada-latvia-2024"
PACKET = BASE / "full-right-high-consensus-context-source-probe/manifest.json"
QUEUE = BASE / "full-right-variant-review-queue-development.json"
SCORES = BASE / "full-right-all-proposal-context-review-development.json"
OUT = BASE / "full-right-high-consensus-context-source-audit.json"

# Three-frame source-pixel review after packet selection. This is not an
# independent physical throw or complete track annotation.
CLASSES = {
    "R0001": "moving_stone_body_pixels",
    "R0010": "moving_stone_body_pixels",
    "R0016": "person_or_equipment_pixels",
    "R0017": "person_or_equipment_pixels",
    "R0024": "moving_stone_body_pixels",
    "R0033": "moving_stone_body_pixels",
    "R0045": "moving_stone_body_pixels",
    "R0048": "person_or_equipment_pixels",
    "R0055": "mixed_stone_person_or_equipment_pixels_identity_uncertain",
    "R0060": "moving_stone_body_pixels",
    "R0067": "moving_stone_body_pixels",
    "R0074": "moving_stone_body_pixels",
    "R0075": "person_or_equipment_pixels",
    "R0086": "moving_stone_body_pixels",
    "R0100": "moving_stone_body_pixels",
    "R0104": "person_or_equipment_pixels",
    "R0106": "person_or_equipment_pixels",
    "R0107": "person_or_equipment_pixels",
    "R0109": "moving_stone_body_pixels",
    "R0117": "person_or_equipment_pixels",
}


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def main():
    packet = json.loads(PACKET.read_text())
    queue = json.loads(QUEUE.read_text())
    scores = json.loads(SCORES.read_text())
    if (
        packet["review_queue_sha256"] != digest(QUEUE)
        or packet["full_context_score_sha256"] != digest(SCORES)
        or len(
            {
                packet["source_video_sha256"],
                queue["source_video_sha256"],
                scores["source_video_sha256"],
            }
        )
        != 1
    ):
        raise ValueError("Probe lineage mismatch")
    for page, expected in packet["page_sha256"].items():
        if digest(PACKET.parent / page) != expected:
            raise ValueError("Source page changed")
    score_rows = {row["proposal_id"]: row for row in scores["proposals"]}
    if {row["review_group_id"] for row in packet["rows"]} != set(CLASSES) or len(
        packet["rows"]
    ) != len(CLASSES):
        raise ValueError("High-consensus probe inventory changed")
    rows = []
    for item in packet["rows"]:
        gid, pid = item["review_group_id"], item["proposal_id"]
        score = score_rows[pid]
        if score["review_group_id"] != gid or score["sample_times_s"] != item["sample_times_s"]:
            raise ValueError("Source packet and score sample differ")
        rows.append(
            {
                "review_group_id": gid,
                "proposal_id": pid,
                "group_context_priority": item["context_review_priority"],
                "proposal_context_tier": score["frozen_paired_context_tier"],
                "source_pixel_class": CLASSES[gid],
                "median_nonice_ring_fraction": score["median_nonice_ring_fraction"],
                "median_underpoint_nonice_fraction": score["median_underpoint_nonice_fraction"],
                "source_page": "full-right-high-consensus-context-source-probe/" + item["page"],
                "physical_throw_verified": False,
            }
        )
    counts = Counter((row["group_context_priority"], row["source_pixel_class"]) for row in rows)
    expected = {
        ("has_clear_context_proposal", "moving_stone_body_pixels"): 9,
        ("has_clear_context_proposal", "person_or_equipment_pixels"): 1,
        ("all_proposals_context_cluttered_review", "moving_stone_body_pixels"): 2,
        ("all_proposals_context_cluttered_review", "person_or_equipment_pixels"): 7,
        (
            "all_proposals_context_cluttered_review",
            "mixed_stone_person_or_equipment_pixels_identity_uncertain",
        ): 1,
    }
    if counts != expected:
        raise ValueError(f"Source-class counts changed: {counts}")
    result = {
        "status": "postscore_selected_high_consensus_source_pixel_audit_not_throw_truth",
        "source_video_sha256": queue["source_video_sha256"],
        "input_sha256": {
            "queue": digest(QUEUE),
            "full_context_scores": digest(SCORES),
            "source_packet_manifest": digest(PACKET),
        },
        "runner_sha256": digest(Path(__file__)),
        "selection_rule": packet["selection"],
        "reviewed_group_count": len(rows),
        "source_class_counts_by_group_priority": {
            priority: {
                cls: counts[priority, cls]
                for cls in (
                    "moving_stone_body_pixels",
                    "person_or_equipment_pixels",
                    "mixed_stone_person_or_equipment_pixels_identity_uncertain",
                )
            }
            for priority in ("has_clear_context_proposal", "all_proposals_context_cluttered_review")
        },
        "stone_pixels_in_all_cluttered_groups": ["R0067", "R0109"],
        "person_pixels_in_selected_clear_group": ["R0117"],
        "rows": rows,
        "limitations": [
            "Only one proposal prefix per group was reviewed; other group members may differ.",
            "The ten clear groups are a deterministic time-spaced sample, not a random or exhaustive estimate.",
            "Source-pixel classes were assigned after proposal/context outputs; this is not independent physical throw truth.",
            "A moving stone body in three frames does not establish a full delivery, release or settle.",
            "The observed counterexamples prohibit treating clear as confirmed throw or cluttered as no throw.",
        ],
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                "reviewed": len(rows),
                "stone_in_all_cluttered": result["stone_pixels_in_all_cluttered_groups"],
                "person_in_clear": result["person_pixels_in_selected_clear_group"],
            }
        )
    )


if __name__ == "__main__":
    main()
