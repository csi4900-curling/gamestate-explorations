"""Export lossless Czech cross-view episodes with patch and pixel evidence."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from source_diverse_episode_handoff import build_episode_handoff

BASE = ROOT / "validation/throw-event-benchmark/canada-czech-2024"
VIDEO = BASE / "source-360p.mp4"
EPISODES = BASE / "full-corridor-right-episodes-first-transfer.json"
STATES = BASE / "full-corridor-right-episode-partial-states-first-transfer.json"
SCORES = BASE / "full-right-source-diverse-patch-transfer-development.json"
OVERLAP = BASE / "full-cross-resolution-receiving-path-overlap-development.json"
AUDITS = {
    "right_only": BASE / "full-right-only-source-diverse-pixel-audit.json",
    "linked_disagreement": BASE / "full-linked-right-patch-disagreement-pixel-audit.json",
    "positive_one_to_one_sample": BASE / "full-linked-positive-patch-pixel-audit.json",
}
OUT = BASE / "full-source-diverse-episode-state-handoff-development.json"


def digest(path):
    h = sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def main():
    if OUT.exists():
        raise ValueError("Episode evidence handoff already exists")
    episodes, states, scores = (json.loads(path.read_text()) for path in (
        EPISODES, STATES, SCORES))
    overlap = json.loads(OVERLAP.read_text())
    audits = {name: json.loads(path.read_text()) for name, path in AUDITS.items()}
    source_hash = digest(VIDEO)
    if (episodes["source_sha256"] != source_hash or
            states["source_sha256"] != source_hash or
            scores["source_video_sha256"] != source_hash or
            overlap["source_video_sha256"] != source_hash or
            overlap["temporal_pair_count"] != len(overlap["rows"]) or
            overlap["pairs_with_at_least_two_shared_samples"] != 42 or
            any(audit["source_video_sha256"] != source_hash
                for audit in audits.values()) or
            states["input_sha256"]["episodes"] != digest(EPISODES)):
        raise ValueError("Czech source or episode/state lineage differs")
    rows, priorities = build_episode_handoff(episodes, states, scores, audits,
                                              overlap["rows"])
    pixel_counts = Counter(right["sampled_source_pixel_class"]
                           for row in rows for right in row[
                               "right_proposal_evidence"])
    if pixel_counts != {None: 72, "person_or_equipment_pixels": 38,
                        "moving_stone_pixels": 21}:
        raise ValueError("Source-pixel review coverage changed")
    if sum(row["state_status"] == "partial_board_observed"
           for row in rows) != 66:
        raise ValueError("Partial-board conservation failed")
    result = {
        "status": "lossless_czech_source_diverse_episode_state_handoff_not_event_truth",
        "source_video_sha256": source_hash,
        "input_sha256": {"episodes": digest(EPISODES), "partial_states": digest(STATES),
                         "patch_scores": digest(SCORES),
                         "cross_resolution_overlap": digest(OVERLAP),
                         **{name + "_pixel_audit": digest(path)
                            for name, path in AUDITS.items()}},
        "join_code_sha256": digest(ROOT / "prototype/source_diverse_episode_handoff.py"),
        "runner_sha256": digest(Path(__file__)),
        "episode_count": len(rows),
        "left_candidate_count": episodes["original_left_candidate_count"],
        "right_proposal_count": episodes["right_proposal_count"],
        "partial_board_count": sum(row["state_status"] ==
                                   "partial_board_observed" for row in rows),
        "temporal_cross_resolution_pair_count": sum(len(row[
            "cross_resolution_candidate_pair_evidence"]) for row in rows),
        "pairs_with_at_least_two_exact_shared_samples": sum(
            pair["sampled_time_overlap_count"] >= 2 for row in rows for pair
            in row["cross_resolution_candidate_pair_evidence"]),
        "reviewed_right_prefix_pixel_counts": {
            "moving_stone_pixels": pixel_counts["moving_stone_pixels"],
            "person_or_equipment_pixels": pixel_counts[
                "person_or_equipment_pixels"],
            "unreviewed": pixel_counts[None],
        },
        "evidence_review_priority_counts": priorities,
        "episodes": rows,
        "limitations": [
            "All 116 left and 131 right candidate IDs are conserved, including source-reviewed people; review priorities do not accept or reject physical throws.",
            "A stone-pixel patch and temporal camera match do not verify a physical stone identity or delivery.",
            "Partial boards are camera-local observations and cannot complete a simulation-ready game state.",
            "Source-pixel audits are selected same-agent postscore development evidence, not independent event truth or full-match F1.",
        ],
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"episodes": len(rows), "left": result["left_candidate_count"],
                      "right": result["right_proposal_count"],
                      "partial_boards": result["partial_board_count"],
                      "priorities": priorities}))


if __name__ == "__main__":
    main()
