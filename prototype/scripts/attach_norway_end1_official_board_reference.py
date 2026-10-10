"""Attach independent PDF post-shot board diagrams to the end-one sequence."""

from hashlib import sha256
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SEQUENCE = ROOT / "validation/official-shot-sequence/norway-end1-16-shot-sequence-hypothesis-first.json"
BOARDS = ROOT / "validation/official-shot-sequence/pwg2022-canada-norway-official-boards.json"
OUTPUT = ROOT / "validation/official-shot-sequence/norway-end1-sequence-official-board-reference-first.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first end-one board reference join")
    sequence = json.loads(SEQUENCE.read_text())
    boards = json.loads(BOARDS.read_text())
    if len(sequence["rows"]) != 16 or boards["ends"][0]["end"] != 1:
        raise SystemExit("Expected 16 end-one sequence rows and official board diagrams")
    reference = boards["ends"][0]["shots"]
    if len(reference) != 16:
        raise SystemExit("Expected 16 official end-one boards")
    rows = []
    for hypothesis, board in zip(sequence["rows"], reference):
        if hypothesis["official_shot_id"] != board["official_shot_id"]:
            raise SystemExit("Official shot IDs differ between sequence and board")
        rows.append({
            "shot_number": hypothesis["shot_number"],
            "official_shot_id": hypothesis["official_shot_id"],
            "video_candidate_shot_id": hypothesis["video_candidate_shot_id"],
            "provisional_delivery_window_s": hypothesis["provisional_delivery_window_s"],
            "official_post_shot_board_source": "independent_official_pdf_diagram",
            "official_post_shot_stones": board["stones"],
            "official_post_shot_stone_counts": board["stone_counts"],
            "official_diagram_review_flags": board["review_flags"],
            "video_post_shot_board_observed": False,
            "video_to_official_board_transition_verified": False,
            "physical_stone_identity_verified": False,
            "simulation_ready": False,
        })
    output = {
        "status": "official_post_shot_board_reference_join_not_video_game_state",
        "sequence_hypothesis_sha256": digest(SEQUENCE),
        "official_boards_sha256": digest(BOARDS),
        "runner_sha256": digest(Path(__file__)),
        "coordinate_definition": "house_radius_coordinates from official PDF diagram extraction",
        "shot_count": len(rows),
        "official_symbol_count": sum(len(row["official_post_shot_stones"]) for row in rows),
        "boards_with_review_flags": sum(bool(row["official_diagram_review_flags"]) for row in rows),
        "rows": rows,
        "limitations": [
            "Official PDF board diagrams are independent shot-order references, not video-derived observations.",
            "The sequence-to-video join is a development hypothesis with provisional event boundaries.",
            "Diagram symbols do not provide stone velocity, physical identity, or full ice positions.",
            "Shot 16 has a low-fill review flag; none of these rows is simulation-ready.",
        ],
    }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n")
    print({"shot_count": output["shot_count"],
           "official_symbol_count": output["official_symbol_count"],
           "boards_with_review_flags": output["boards_with_review_flags"]})


if __name__ == "__main__":
    main()
