"""Freeze a candidate-to-global-motion evidence graph for Norway."""

from hashlib import sha256
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from prototype.global_motion_links import link_candidate_windows


CATALOG = ROOT / "validation/official-shot-sequence/norway-global-shot-scoped-cap-motion-first.json"
CANDIDATES = ROOT / "validation/official-shot-sequence/norway-full-event-motion-cut-aware-v2.json"
OUTPUT = ROOT / "validation/official-shot-sequence/norway-global-cap-motion-candidate-links-first.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first candidate-to-global-motion graph")
    catalog = json.loads(CATALOG.read_text())
    candidates = json.loads(CANDIDATES.read_text())
    if catalog["source_video_sha256"] != candidates["source_video_sha256"]:
        raise SystemExit("Catalog and candidates refer to different video sources")
    if catalog["camera_shot_count"] != len(catalog["shots"]):
        raise SystemExit("Catalog camera-shot count disagrees")
    if catalog["episode_count"] != sum(len(s["tracks"]) for s in catalog["shots"]):
        raise SystemExit("Catalog episode count disagrees")
    graph = link_candidate_windows(candidates["rows"], catalog["shots"])
    if graph["candidate_count"] != candidates["candidate_count"]:
        raise SystemExit("Candidate count disagrees")
    result = {
        "status": "source_only_global_motion_candidate_graph_not_one_to_one_throw_assignment",
        "global_motion_catalog_sha256": digest(CATALOG),
        "candidate_source_sha256": digest(CANDIDATES),
        "link_code_sha256": digest(ROOT / "prototype/global_motion_links.py"),
        "runner_sha256": digest(Path(__file__)),
        **graph,
        "limitations": [
            "Colour-compatible temporal overlap is a possible evidence link, not a physical throw assignment.",
            "One global track can link to multiple candidate windows; an exclusive link does not prove it is a delivered stone.",
            "The catalog may contain false cap tracks and may miss real throws at 1 Hz.",
            "Source camera-shot boundaries are development evidence, not independent throw labels.",
        ],
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print({key: result[key] for key in
           ("catalogue_episode_count", "candidate_count", "candidate_episode_edge_count",
            "shared_by_multiple_candidates_episode_count", "unlinked_catalogue_episode_count",
            "candidate_motion_status_counts")})


if __name__ == "__main__":
    main()
