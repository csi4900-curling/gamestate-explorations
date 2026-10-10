"""Record source-backed local E019 red-stone continuity through contact."""

from hashlib import sha256
import json
from math import dist
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark/canada-czech-2024"
PACKET = BASE / "e019-settle-continuity-source-probe"
MOTION = BASE / "full-match-motion-merged-postscore.json"
BOARD = BASE / "full-match-partial-boards-postscore.json"
OUT = BASE / "e019-settle-continuity-source-audit.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    manifest_path = PACKET / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    if (digest(PACKET / "dense-contact-sheet.jpg") != manifest["sheet_sha256"]
            or manifest["input_sha256"] != {"motion": digest(MOTION),
                                             "board": digest(BOARD)}):
        raise ValueError("E019 source packet or input changed")
    samples = manifest["samples"]
    if (len(samples) != 8 or
            [r["source_time_s_requested"] for r in samples] !=
            [686.0, 686.25, 686.5, 686.75, 687.0, 687.25, 687.5, 688.0]):
        raise ValueError("E019 dense sample inventory changed")
    motion = json.loads(MOTION.read_text())
    boards = json.loads(BOARD.read_text())
    path = next(r for r in motion["rows"] if r["candidate_id"] == "S20")[
        "selection"]["path"]
    by_time = {p["source_time_s"]: p for p in path}
    board = next(r for r in boards["rows"] if r["candidate_id"] == "S20")
    first_red = next(s for f in board["frames"] if f["source_time_s"] == 687.0
                     for s in f["stones"] if s["colour"] == "red")
    second_red = next(s for f in board["frames"] if f["source_time_s"] == 688.0
                      for s in f["stones"] if s["colour"] == "red")
    red_board_row = next(s for s in board["board"]["stones"]
                         if s["colour"] == "red")
    result = {
        "status": "same_agent_dense_source_visual_continuity_development_not_game_truth",
        "source_video_sha256": manifest["source_video_sha256"],
        "manifest_sha256": digest(manifest_path),
        "source_sheet_sha256": manifest["sheet_sha256"],
        "input_sha256": manifest["input_sha256"],
        "runner_sha256": digest(Path(__file__)),
        "episode_id": "E019",
        "left_candidate_id": "S20",
        "right_proposal_id": "R01:A025",
        "source_pixel_observations": [
            {"interval_s": [686.0, 686.5],
             "observation": "red stone visibly approaches the yellow stone"},
            {"interval_s": [686.5, 687.0],
             "observation": "red and yellow bodies touch/overlap in the local crop"},
            {"interval_s": [687.0, 688.0],
             "observation": "red stone remains near the board red detection while the contacted yellow stone separates"},
        ],
        "local_red_path_to_board_visual_continuity":
            "supported_by_dense_source_frames_around_contact",
        "last_motion_sample": {"time_s": 686.5,
                               "pixel_center_1080": by_time[686.5]["pixel_center"]},
        "first_board_red_detection": {"time_s": 687.0,
                                      "pixel_center_1080": first_red[
                                          "pixel_center"]},
        "next_board_red_detection": {"time_s": 688.0,
                                     "pixel_center_1080": second_red[
                                         "pixel_center"]},
        "last_motion_to_first_board_red_distance_px_1080": round(dist(
            by_time[686.5]["pixel_center"], first_red["pixel_center"]), 3),
        "board_red_local_observation_first_last_s": [
            red_board_row["first_seen_s"], red_board_row["last_seen_s"]],
        "physical_throw_identity_independently_verified": False,
        "full_contact_dynamics_reconstructed": False,
        "complete_game_state": False,
        "simulation_ready": False,
        "limitations": [
            "The local visual-continuity judgment is same-agent source review, not independent event or persistent-identity ground truth.",
            "The overlapping stone bodies make cap centers ambiguous during contact; the 13-pixel endpoint gap is not a calibrated physical displacement.",
            "The crop does not establish the complete board, release time, spin, collision impulse or metric trajectory uncertainty.",
        ],
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"episode": "E019", "source_frames": len(samples),
                      "pixel_gap": result[
                          "last_motion_to_first_board_red_distance_px_1080"]}))


if __name__ == "__main__":
    main()
