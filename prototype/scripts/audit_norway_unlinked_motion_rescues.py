"""Freeze adjacent-origin review proposals from unlinked Norway motion."""

from hashlib import sha256
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from prototype.unlinked_motion_rescue import find_adjacent_origin_proposals


BASE = ROOT / "validation/curlobserver-learned-probe/canada-norway-full-transfer"
GLOBAL = ROOT / "validation/official-shot-sequence/norway-global-shot-scoped-cap-motion-first.json"
LINKS = (
    ROOT / "validation/official-shot-sequence/norway-global-cap-motion-candidate-links-first.json"
)
ORIGINS = BASE / "shot-origin.json"
MANIFEST = BASE / "shot-review/manifest.json"
CANDIDATES = ROOT / "validation/official-shot-sequence/norway-full-event-motion-cut-aware-v2.json"
OUTPUT = (
    ROOT / "validation/official-shot-sequence/norway-unlinked-motion-rescue-proposals-first.json"
)


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first unlinked-motion rescue audit")
    global_catalog = json.loads(GLOBAL.read_text())
    links = json.loads(LINKS.read_text())
    origins = json.loads(ORIGINS.read_text())
    manifest = json.loads(MANIFEST.read_text())
    candidates = json.loads(CANDIDATES.read_text())
    source_hashes = {
        global_catalog["source_video_sha256"],
        origins["source_sha256"],
        manifest["source_sha256"],
        candidates["source_video_sha256"],
    }
    if len(source_hashes) != 1 or links["global_motion_catalog_sha256"] != digest(GLOBAL):
        raise SystemExit("Inputs do not describe the same frozen video/catalog")
    episodes = [track for shot in global_catalog["shots"] for track in shot["tracks"]]
    proposals = find_adjacent_origin_proposals(
        links["episodes"], episodes, origins["rows"], manifest["shots"], candidates["rows"]
    )
    result = {
        "status": "source_only_unlinked_motion_adjacent_origin_review_proposals_not_verified_throws",
        "input_sha256": {
            "global_motion_catalog": digest(GLOBAL),
            "candidate_link_graph": digest(LINKS),
            "shot_origin": digest(ORIGINS),
            "camera_shot_manifest": digest(MANIFEST),
            "candidate_ledger": digest(CANDIDATES),
        },
        "selection_code_sha256": digest(ROOT / "prototype/unlinked_motion_rescue.py"),
        "runner_sha256": digest(Path(__file__)),
        "selection_rule": {
            "unlinked_global_cap_track": True,
            "immediately_previous_camera_shot_origin_probability_at_least": 0.9,
            "origin_shot_duration_at_least_s": 5.0,
            "motion_onset_after_receiving_cut_at_most_s": 1.0,
            "candidate_origin_absent_or_colour_conflicted": True,
            "post_hoc_development_rule": True,
        },
        "proposal_count": len(proposals),
        "proposals": proposals,
        "limitations": [
            "The rule was selected after inspecting Norway unlinked tracks; its yield is not an unbiased recall estimate.",
            "Origin scores and cap tracks share source footage and are not independent labels.",
            "A receiving cap may be an old stone; colour conflict can result from a collision, not a wrong candidate colour.",
            "No candidate is automatically inserted, recoloured, or matched to an official shot.",
        ],
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print(
        [
            (row["origin_shot_id"], row["receiving_episode_id"], row["candidate_status"])
            for row in proposals
        ]
    )


if __name__ == "__main__":
    main()
