"""Join independent official shot order with extracted post-shot board states."""

from collections import Counter
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SHOTS = ROOT / "validation/official-shot-sequence/pwg2022-official-shot-ledger.json"
BOARDS = ROOT / "validation/official-shot-sequence/pwg2022-official-board-diagrams.json"
OUTPUT = ROOT / "validation/official-shot-sequence/pwg2022-official-game-state-reference.json"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first official state reference")
    shot_reference = json.loads(SHOTS.read_text())
    board_reference = json.loads(BOARDS.read_text())
    if board_reference["shot_ledger_sha256"] != digest(SHOTS):
        raise ValueError("Board diagrams use a different shot ledger")
    board_games = {game["official_game_code"]: game for game in board_reference["games"]}
    games = []
    for game in shot_reference["games"]:
        board_game = board_games[game["official_game_code"]]
        board_ends = {end["end"]: end for end in board_game["ends"]}
        transitions = []
        for end in game["ends"]:
            board_end = board_ends[end["end"]]
            board_shots = {row["official_shot_id"]: row for row in board_end["shots"]}
            if len(board_shots) != end["shot_count"]:
                raise ValueError("Missing or duplicate shot diagram")
            previous_id = None
            for shot in end["shots"]:
                identifier = shot["official_shot_id"]
                board = board_shots[identifier]
                stones = [{
                    "colour": row["colour"],
                    "x_house_radii": row["house_radius_coordinates"][0],
                    "longitudinal_house_radii": row["house_radius_coordinates"][1],
                    "diagram_pixel": row["diagram_pixel"],
                    "near_diagram_edge": row["near_diagram_edge"],
                    "low_fill_margin": row["low_fill_margin"],
                } for row in board["stones"]]
                counts = Counter(row["colour"] for row in stones)
                if any(counts[colour] != board["stone_counts"][colour]
                       for colour in ("red", "yellow")):
                    raise ValueError("Diagram stone count mismatch")
                transitions.append({
                    "official_shot_id": identifier,
                    "end": end["end"],
                    "shot_number": shot["shot_number"],
                    "delivery_team": shot["team"],
                    "delivery_handle_colour": game["team_handle_colours"][shot["team"]],
                    "shooter": shot["shooter"],
                    "shot_type": shot["shot_type"],
                    "official_evaluation_percent": shot["evaluation_percent"],
                    "rotation": shot["rotation"],
                    "official_notes": shot["notes"],
                    "pre_state_shot_id": previous_id,
                    "pre_state_is_empty_end_start": previous_id is None,
                    "post_state": {
                        "coordinate_system": "unitless_house_outer_radius",
                        "red_stone_count": counts["red"],
                        "yellow_stone_count": counts["yellow"],
                        "stone_symbols": stones,
                        "diagram_review_flags": board["review_flags"],
                    },
                    "source_pdf_page": end["pdf_page"],
                    "source_diagram_image_sha256": board["diagram_image_sha256"],
                    "video_release_time_s": None,
                    "video_trajectory": None,
                })
                previous_id = identifier
        games.append({
            "official_game_code": game["official_game_code"],
            "teams": game["teams"],
            "team_handle_colours": game["team_handle_colours"],
            "source_video_sha256": game["source_video_sha256"],
            "official_shot_count": game["official_shot_count"],
            "transitions": transitions,
        })
    output = {
        "status": "official_pdf_postshot_state_reference_without_video_reconstruction",
        "official_pdf_url": shot_reference["official_pdf_url"],
        "official_pdf_sha256": shot_reference["official_pdf_sha256"],
        "official_shot_ledger_sha256": digest(SHOTS),
        "official_board_diagrams_sha256": digest(BOARDS),
        "runner_sha256": digest(Path(__file__)),
        "coordinate_definition": {
            "x_house_radii": "diagram pixel x minus 150, divided by 120; positive right on page",
            "longitudinal_house_radii": "distance from house centre toward the back of the sheet, divided by 120",
            "physical_metres_calibrated": False,
            "z_coordinate_available": False,
        },
        "transition_count": sum(len(game["transitions"]) for game in games),
        "games": games,
        "limitations": [
            "This is an independent official PDF reference, not video-derived board reconstruction.",
            "Diagram symbols are anonymous; persistent physical stone identities and trajectories are not recovered.",
            "Outlined prior positions are excluded; near-edge symbols and low-fill detections retain explicit uncertainty.",
            "No video timestamps, release points, physical metres, or 3D coordinates are available in this reference.",
            "Simulation must treat diagram positions as source observations and must not infer unobserved movement or collisions from adjacent states alone.",
        ],
    }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n")
    print(output["transition_count"], [len(game["transitions"]) for game in games])


if __name__ == "__main__":
    main()
