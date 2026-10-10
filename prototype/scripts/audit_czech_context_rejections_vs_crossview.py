"""Compare Czech context vetoes with the earlier cross-view evidence ledger."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark"
RUN = BASE / "layout-router/czech24-full-camera-motion-v1"
RAW = RUN / "run-02/raw.json"
REJECTIONS = RUN / "large-surrounding-motion-rejections-development.json"
OLD_RAW = BASE / "canada-czech-2024/full-match-stage1-raw-postscore.json"
HANDOFF = BASE / "canada-czech-2024/full-source-diverse-episode-state-handoff-development.json"
RIGHT_PATCH = BASE / "canada-czech-2024/full-right-source-diverse-patch-transfer-development.json"
OUT = RUN / "large-motion-crossview-reconciliation-development.json"


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def main():
    if OUT.exists():
        raise ValueError("Cross-view reconciliation already exists")
    raw, rejects, old_raw, handoff, right = (json.loads(path.read_text()) for
                                           path in (RAW, REJECTIONS, OLD_RAW,
                                                        HANDOFF, RIGHT_PATCH))
    source = raw["source_sha256"]
    if any(value != source for value in (
            rejects["source_sha256"], old_raw["source_sha256"],
            handoff["source_video_sha256"], right["source_video_sha256"])):
        raise ValueError("Source hash differs")
    if handoff["input_sha256"]["patch_scores"] != digest(RIGHT_PATCH):
        raise ValueError("Handoff references different right-patch evidence")
    old_signature = [(row["id"], row["crossing_time_s"], row["colour"])
                     for row in old_raw["events"]]
    new_signature = [(row["id"], row["crossing_time_s"], row["colour"])
                     for row in raw["events"]]
    if old_signature != new_signature or \
            rejects["input_sha256"]["raw"] != digest(RAW):
        raise ValueError("New and old raw proposals differ")
    episode_by_id = {}
    for episode in handoff["episodes"]:
        for member in episode.get("left_members", []):
            id = member["full_match_candidate_id"]
            if id in episode_by_id:
                raise ValueError(f"Repeated full-match ID: {id}")
            episode_by_id[id] = (episode, member)
    right_by_id = {row["right_proposal_id"]: row for row in right["rows"]}
    if len(right_by_id) != len(right["rows"]):
        raise ValueError("Repeated right proposal ID")
    rows = []
    for rejected in rejects["rows"]:
        id = rejected["candidate_id"]
        match = episode_by_id.get(id)
        if match is None:
            rows.append({"candidate_id": id, "old_handoff_status":
                         "no_old_left_member"})
            continue
        episode, member = match
        rights = []
        for right_id in episode["right_proposal_ids"]:
            row = right_by_id[right_id]
            rights.append({"right_proposal_id": right_id,
                           "passage_time_s": row["passage_time_s"],
                           "lag_from_left_passage_s": row["passage_time_s"] -
                                rejected["passage_time_s"],
                           "positive_patch_count": row["positive_patch_count"],
                           "sampled_patch_count": len(row["samples"]),
                           "source_pixel_class_in_handoff": next((
                               x["sampled_source_pixel_class"] for x in
                               episode["right_proposal_evidence"] if
                               x["right_proposal_id"] == right_id), None)})
        rows.append({
            "candidate_id": id,
            "passage_time_s": rejected["passage_time_s"],
            "old_episode_id": episode["episode_id"],
            "old_handoff_status": "joined",
            "old_screen_accepted": member["screen_accepted"],
            "old_screen_status": member["screen_status"],
            "right_proposals": rights,
            "cross_resolution_candidate_pair_evidence": [row for row in
                episode["cross_resolution_candidate_pair_evidence"] if
                row["left_candidate_id"] == id],
            "old_partial_board_status": episode["state_status"],
            "old_partial_board_observation_count": len((
                episode.get("post_event_partial_board") or {}).get("stones", [])),
        })
    OUT.write_text(json.dumps({
        "status": "development_cross_pipeline_reconciliation_not_physical_throw_labels",
        "source_sha256": source,
        "input_sha256": {"current_raw": digest(RAW),
                         "current_rejections": digest(REJECTIONS),
                         "old_raw": digest(OLD_RAW),
                         "old_handoff": digest(HANDOFF),
                         "old_right_patch": digest(RIGHT_PATCH)},
        "runner_sha256": digest(Path(__file__)),
        "rejection_count": len(rows),
        "old_screen_accepted_count": sum(row.get("old_screen_accepted", False)
                                         for row in rows),
        "old_screen_status_counts": dict(Counter(row.get("old_screen_status",
                                                    row["old_handoff_status"])
                                                  for row in rows)),
        "rows": rows,
        "limitations": [
            "The older screen is development-fitted and its acceptances include source-reviewed non-stone paths.",
            "Time, colour, and cross-resolution pixel overlap do not establish physical identity across cameras.",
            "A partial post-event board is not a verified complete game state or physical settle time.",
        ],
    }, indent=2) + "\n")
    print(json.dumps({"rejections": len(rows),
                      "old_screen_accepted": sum(row.get("old_screen_accepted", False)
                                                 for row in rows),
                      "with_old_right_proposals": sum(bool(row.get("right_proposals"))
                                                      for row in rows)}))


if __name__ == "__main__":
    main()
