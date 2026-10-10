"""Freeze all 128 official shot slots with separate source-video state evidence."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.full_match_state_handoff import build_state_rows


BASE = ROOT / "validation/official-shot-sequence"
PATHS = {
    "scaffold": BASE / "norway-full-match-official-counter-slot-scaffold-first.json",
    "official_shots": BASE / "pwg2022-canada-norway-official-ledger.json",
    "official_boards": BASE / "pwg2022-canada-norway-official-boards.json",
    "source_boards": BASE / "norway-full-candidate-post-counter-image-boards-v3.json",
    "counter_gaps": BASE / "norway-counter-gap-inventory-first.json",
    "orientation_cues": BASE / "norway-motion-approach-orientation-cues-first.json",
    "diagram_postscore": BASE / "norway-full-post-counter-image-board-postscore-first.json",
}
OUTPUT = BASE / "norway-full-match-evidence-state-handoff-first.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("First full-match state handoff already exists")
    data = {key: json.loads(path.read_text()) for key, path in PATHS.items()}
    official = data["official_shots"]
    boards = data["official_boards"]
    scan = data["source_boards"]
    scaffold = data["scaffold"]
    if len({official["source_video_sha256"], boards["source_video_sha256"],
            scan["source_video_sha256"]}) != 1:
        raise SystemExit("Video source hash conflict")
    if scaffold["input_sha256"]["official_shot_ledger"] != digest(PATHS["official_shots"]):
        raise SystemExit("Scaffold/official-ledger hash conflict")
    if scaffold["input_sha256"]["candidate_ledger"] != scan["candidate_ledger_sha256"]:
        raise SystemExit("Scaffold/source-candidate hash conflict")
    if data["diagram_postscore"]["input_sha256"]["source_scan"] != digest(PATHS["source_boards"]):
        raise SystemExit("Postscore/source-scan hash conflict")
    if data["counter_gaps"]["input_sha256"]["slot_scaffold"] != digest(PATHS["scaffold"]):
        raise SystemExit("Gap/scaffold hash conflict")
    gap_proposals = [row["unique_order_colour_display_proposal"]
                     for row in data["counter_gaps"]["gaps"]
                     if row["unique_order_colour_display_proposal"]]
    if len(gap_proposals) != 1:
        raise SystemExit("Unique gap proposal count changed")
    rows = build_state_rows(
        scaffold["slots"],
        [shot for end in official["ends"] for shot in end["shots"]],
        [shot for end in boards["ends"] for shot in end["shots"]],
        scan["rows"], gap_proposals, data["orientation_cues"]["rows"],
        data["diagram_postscore"]["groups"])
    if len({len(rows), official["official_shot_count"],
            scaffold["official_shot_slot_count"]}) != 1:
        raise SystemExit("Shot slot count changed")
    basis_counts = Counter(row["video_event_evidence"]["association_basis"] for row in rows)
    result = {
        "status": "full_match_reference_and_partial_video_evidence_handoff_not_complete_game_state",
        "source_video_sha256": official["source_video_sha256"],
        "input_sha256": {key: digest(path) for key, path in PATHS.items()},
        "handoff_code_sha256": digest(ROOT / "prototype/full_match_state_handoff.py"),
        "runner_sha256": digest(Path(__file__)),
        "official_slot_count": len(rows),
        "association_basis_counts": dict(basis_counts),
        "slots_with_stable_video_house_observation": sum(
            row["video_post_shot_state"]["status"] == "partial_image_house_observations"
            for row in rows),
        "slots_with_retrospective_diagram_comparison": sum(any(
            group["retrospective_official_diagram_comparison"] is not None
            for group in row["video_post_shot_state"]["camera_groups"]) for row in rows),
        "video_physics_simulation_ready_count": sum(row["video_physics_simulation_ready"] for row in rows),
        "slots": rows,
        "limitations": [
            "Official PDF positions and rotation direction are independent reference data, not inferred from video.",
            "Official diagrams cover a schematic portion of the sheet, not a complete physical game state.",
            "Video event associations, including counter links, remain provisional and not independently labelled.",
            "Video boards are partial image-relative observations; uncertain orientation is retained.",
            "No video-derived 3D geometry, verified release/settle time, turn count, or simulation-ready physical replay is claimed.",
        ],
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print({key: result[key] for key in
           ("official_slot_count", "association_basis_counts",
            "slots_with_stable_video_house_observation",
            "slots_with_retrospective_diagram_comparison",
            "video_physics_simulation_ready_count")})


if __name__ == "__main__":
    main()
