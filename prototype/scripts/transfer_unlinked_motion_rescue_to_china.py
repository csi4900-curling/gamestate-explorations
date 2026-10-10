"""Apply the frozen Norway link and adjacent-origin proposal rules to China."""

from hashlib import sha256
import json
from math import ceil, floor
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from prototype.global_motion_links import link_candidate_windows
from prototype.unlinked_motion_rescue import find_adjacent_origin_proposals


BASE = ROOT / "validation/curlobserver-learned-probe/china-full-transfer"
CATALOG = ROOT / "validation/official-shot-sequence/china-global-shot-scoped-cap-motion-first.json"
LEDGER = BASE / "fused-shot-candidates-replay-following-rescue-v2.json"
ORIGINS = BASE / "unlabelled-shot-origin-inference.json"
MANIFEST = BASE / "shot-review/manifest.json"
GRAPH = ROOT / "validation/official-shot-sequence/china-global-cap-motion-candidate-links-first.json"
PROPOSALS = ROOT / "validation/official-shot-sequence/china-unlinked-motion-rescue-transfer-first.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    if GRAPH.exists() or PROPOSALS.exists():
        raise SystemExit("Output exists; preserve first China transfer")
    catalog = json.loads(CATALOG.read_text())
    ledger = json.loads(LEDGER.read_text())
    origins = json.loads(ORIGINS.read_text())
    manifest = json.loads(MANIFEST.read_text())
    source_hashes = {catalog["source_video_sha256"], ledger["source_sha256"],
                     origins["source_sha256"], manifest["source_sha256"]}
    if len(source_hashes) != 1:
        raise SystemExit("China transfer inputs have different video sources")
    if catalog["shot_manifest_sha256"] != digest(MANIFEST):
        raise SystemExit("Catalog shot manifest changed")
    source_end = manifest["source_interval_s"][1]
    normalized = []
    for row in ledger["events"]:
        start, end = row["delivery_window_s"]
        normalized.append({
            "shot_id": row["shot_id"],
            "counter_id": row["counter_id"],
            "candidate_colour": row["colour"],
            "delivery_window_s": row["delivery_window_s"],
            "search_interval_s": [max(0, floor(start) - 5), min(source_end, ceil(end) + 15)],
        })
    if len(normalized) != ledger["candidate_count"]:
        raise SystemExit("China candidate count disagrees")
    graph = link_candidate_windows(normalized, catalog["shots"])
    graph_result = {
        "status": "source_only_china_global_motion_candidate_links_not_physical_events",
        "input_sha256": {"catalog": digest(CATALOG), "candidate_ledger": digest(LEDGER),
                         "shot_manifest": digest(MANIFEST)},
        "link_code_sha256": digest(ROOT / "prototype/global_motion_links.py"),
        "runner_sha256": digest(Path(__file__)),
        "candidate_search_rule": "Frozen Norway rule: floor(start)-5 through ceil(end)+15 seconds, capped at video end.",
        **graph,
        "limitations": ["Temporal overlap and colour are not physical throw assignment or independent ground truth."],
    }
    episodes = [track for shot in catalog["shots"] for track in shot["tracks"]]
    proposals = find_adjacent_origin_proposals(
        graph["episodes"], episodes, origins["rows"], manifest["shots"], normalized)
    proposal_result = {
        "status": "frozen_norway_unlinked_motion_rule_china_transfer_not_event_f1",
        "input_sha256": {"catalog": digest(CATALOG), "candidate_ledger": digest(LEDGER),
                         "shot_origin": digest(ORIGINS), "shot_manifest": digest(MANIFEST)},
        "link_code_sha256": digest(ROOT / "prototype/global_motion_links.py"),
        "selection_code_sha256": digest(ROOT / "prototype/unlinked_motion_rescue.py"),
        "runner_sha256": digest(Path(__file__)),
        "selection_rule": {
            "unlinked_global_cap_track": True,
            "immediately_previous_camera_shot_origin_probability_at_least": 0.9,
            "origin_shot_duration_at_least_s": 5.0,
            "motion_onset_after_receiving_cut_at_most_s": 1.0,
            "candidate_origin_absent_or_colour_conflicted": True,
            "thresholds_unchanged_from_norway": True,
        },
        "candidate_count": len(normalized),
        "unlinked_catalogue_episode_count": graph["unlinked_catalogue_episode_count"],
        "proposal_count": len(proposals),
        "proposals": proposals,
        "limitations": [
            "Norway-selected development thresholds are transferred unchanged, but this is not independent event validation.",
            "The China candidate ledger is a provisional development ledger; missing or wrong-colour status is relative to it.",
            "No proposed event is inserted or recoloured automatically.",
        ],
    }
    GRAPH.write_text(json.dumps(graph_result, indent=2) + "\n")
    PROPOSALS.write_text(json.dumps(proposal_result, indent=2) + "\n")
    print({"catalogue_episodes": graph["catalogue_episode_count"],
           "candidate_links": graph["candidate_episode_edge_count"],
           "unlinked_episodes": graph["unlinked_catalogue_episode_count"],
           "proposal_count": len(proposals)})


if __name__ == "__main__":
    main()
