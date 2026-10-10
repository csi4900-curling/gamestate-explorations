"""Compare window-clipped and source-wide shot-scoped Norway motion support."""

from hashlib import sha256
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LOCAL = ROOT / "validation/official-shot-sequence/norway-full-event-motion-cut-aware-v2.json"
GLOBAL = ROOT / "validation/official-shot-sequence/norway-global-cap-motion-candidate-links-first.json"
OUTPUT = ROOT / "validation/official-shot-sequence/norway-global-cap-motion-coverage-first.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first global coverage audit")
    local = json.loads(LOCAL.read_text())
    global_links = json.loads(GLOBAL.read_text())
    local_rows = {row["shot_id"]: row for row in local["rows"]}
    global_rows = {row["candidate_id"]: row for row in global_links["candidates"]}
    if set(local_rows) != set(global_rows) or len(local_rows) != 141:
        raise SystemExit("Candidate sets differ")
    local_only = sorted((shot_id for shot_id in local_rows if
                         local_rows[shot_id]["any_supported_motion"] and
                         not global_rows[shot_id]["linked_episode_ids"]),
                        key=lambda s: int(s[1:]))
    global_only = sorted((shot_id for shot_id in local_rows if
                          not local_rows[shot_id]["any_supported_motion"] and
                          global_rows[shot_id]["linked_episode_ids"]),
                         key=lambda s: int(s[1:]))
    origin_edges = [edge for edge in global_links["edges"] if edge["same_origin_camera_shot"]]
    shared = [row for row in global_links["episodes"] if len(row["candidate_ids"]) > 1]
    result = {
        "status": "source_only_local_vs_global_motion_coverage_not_event_f1",
        "local_cut_aware_sha256": digest(LOCAL),
        "global_candidate_links_sha256": digest(GLOBAL),
        "runner_sha256": digest(Path(__file__)),
        "candidate_count": len(local_rows),
        "local_supported_candidates": sum(row["any_supported_motion"] for row in local_rows.values()),
        "global_linked_candidates": sum(bool(row["linked_episode_ids"]) for row in global_rows.values()),
        "local_only_candidate_ids": local_only,
        "global_only_candidate_ids": global_only,
        "global_catalogue_episode_count": global_links["catalogue_episode_count"],
        "global_catalogue_unlinked_episode_count": global_links["unlinked_catalogue_episode_count"],
        "shared_global_episodes": shared,
        "origin_camera_shot_edge_count": len(origin_edges),
        "origin_camera_shot_candidate_count": len({edge["candidate_id"] for edge in origin_edges}),
        "origin_camera_shot_counter_backed_candidate_count": sum(
            global_rows[shot_id]["counter_id"] is not None
            for shot_id in {edge["candidate_id"] for edge in origin_edges}),
        "limitations": [
            "Global catalog tracks are generated once per camera shot, but cap motion is not a physical throw label.",
            "Temporal overlap with a candidate search window can include old stones or adjacent deliveries.",
            "Different scan contexts can add or lose tracks; neither support change proves a candidate is true or false.",
            "Counter-backed is a broadcast proxy, not independent event ground truth.",
        ],
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print({key: result[key] for key in
           ("local_supported_candidates", "global_linked_candidates",
            "local_only_candidate_ids", "global_only_candidate_ids",
            "global_catalogue_episode_count", "global_catalogue_unlinked_episode_count",
            "origin_camera_shot_candidate_count")})


if __name__ == "__main__":
    main()
