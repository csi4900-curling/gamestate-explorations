"""Retrospective sensitivity comparison for source-only dense board scan."""

from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.board_state_comparison import compare_board_observations  # noqa: E402

BASE = ROOT / "validation/official-shot-sequence"
SCAN = BASE / "norway-full-candidate-post-counter-dense-boards-v5.json"
SLOTS = BASE / "norway-full-match-official-counter-slot-scaffold-first.json"
OFFICIAL = BASE / "pwg2022-canada-norway-official-boards.json"
OUTPUT = BASE / "norway-full-dense-board-postscore-v5.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def comparison(stones, side, shot):
    sign = 1 if side == "top" else -1
    video = [{"colour": stone["colour"],
              "canonical_lateral_house_radii": round(sign * stone["image_house_radius_coordinates"][0], 4),
              "longitudinal_house_radii": round(sign * stone["image_house_radius_coordinates"][1], 4)}
             for stone in stones]
    return compare_board_observations(video, shot["stones"],
                                      official_house_center_y=shot["house_center_px"][1])


def summarize(rows, key):
    selected = [r[key] for r in rows if r[key] is not None]
    return {
        "scored_camera_group_count": len(selected),
        "video_stone_count": sum(r["video_stone_count"] for r in selected),
        "matched_stone_count": sum(r["matched_count"] for r in selected),
        "unmatched_video_stone_count": sum(len(r["unmatched_video"]) for r in selected),
        "complete_diagram_symbol_match_group_count": sum(
            r["video_stone_count"] == r["official_symbol_count"] == r["matched_count"] for r in selected),
    }


def main():
    if OUTPUT.exists():
        raise SystemExit("V5 postscore already exists")
    scan = json.loads(SCAN.read_text())
    scaffold = json.loads(SLOTS.read_text())
    official = json.loads(OFFICIAL.read_text())
    if scan["source_video_sha256"] != official["source_video_sha256"]:
        raise SystemExit("Source-video hash conflict")
    if scaffold["input_sha256"]["candidate_ledger"] != scan["input_sha256"]["candidate_ledger"]:
        raise SystemExit("Candidate-ledger hash conflict")
    by_candidate = {r["shot_id"]: r for r in scan["rows"]}
    if len(by_candidate) != len(scan["rows"]):
        raise SystemExit("Duplicate candidate shot IDs")
    by_shot = {shot["official_shot_id"]: shot
               for end in official["ends"] for shot in end["shots"]}
    rows = []
    for slot in scaffold["slots"]:
        if slot["counter_id"] is None or slot["video_candidate_shot_id"] is None:
            continue
        candidate = by_candidate[slot["video_candidate_shot_id"]]
        if (candidate["counter_id"] != slot["counter_id"] or
                candidate["counter_crossing_time_s"] != slot["counter_crossing_time_s"]):
            raise SystemExit("Counter link changed")
        shot = by_shot[slot["official_shot_id"]]
        for group in candidate["camera_shot_boards"]:
            side = group["detected_delivery_side"]
            if side not in ("top", "bottom"):
                continue
            if group["observation_interval_s"][0] < slot["counter_crossing_time_s"] + 2:
                raise SystemExit("Pre-counter group")
            stable = group["stable_image_relative_stones"]
            terminal = group["terminal_stable_image_relative_stones"]
            if not stable:
                continue
            rows.append({
                "official_shot_id": slot["official_shot_id"],
                "video_candidate_shot_id": candidate["shot_id"],
                "post_camera_shot_id": group["camera_shot_id"],
                "source_observation_interval_s": group["observation_interval_s"],
                "stable_comparison": comparison(stable, side, shot),
                "terminal_comparison": comparison(terminal, side, shot) if terminal else None,
            })
    result = {
        "status": "retrospective_dense_sampling_sensitivity_not_event_or_state_validation",
        "input_sha256": {"source_scan": digest(SCAN), "slot_scaffold": digest(SLOTS),
                         "official_boards": digest(OFFICIAL)},
        "comparator_sha256": digest(ROOT / "prototype/board_state_comparison.py"),
        "runner_sha256": digest(Path(__file__)),
        "stable_summary": summarize(rows, "stable_comparison"),
        "terminal_summary": summarize(rows, "terminal_comparison"),
        "rows": rows,
        "limitations": [
            "This is a retrospective comparison on exposed development data, not a frozen held-out score.",
            "Only counter-linked candidates with source-known orientation and stable stones are scored.",
            "The terminal subset favors visibility near camera-shot end and may omit occluded true stones.",
            "Diagram agreement is not complete video state accuracy or verified event identity.",
        ],
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: result[k] for k in ("stable_summary", "terminal_summary")}, indent=2))


if __name__ == "__main__":
    main()
