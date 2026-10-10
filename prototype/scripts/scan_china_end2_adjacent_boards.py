"""Source-pixel scan for adjacent partial boards around China end-2 shots 10–14."""

from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.temporal_board_state import stable_board_stones
from prototype.video_board_observation_v2 import detect_board_stones, detect_overhead_house

BASE = ROOT / "validation/official-shot-sequence"
ALIGNMENT = BASE / "pwg2022-official-counter-alignment.json"
PRIOR = BASE / "pwg2022-temporal-partial-boards.json"
VIDEO = ROOT / "validation/throw-event-benchmark/paralympics-2022-canada-china/source.mp4"
OUTPUT = BASE / "china-end2-adjacent-video-boards-first.json"
SHOT_NUMBERS = (10, 11, 12, 13, 14)
OFFSETS_S = tuple(range(4, 31, 2))


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first adjacent-board scan")
    alignment, prior = (json.loads(path.read_text()) for path in (ALIGNMENT, PRIOR))
    source_hash = digest(VIDEO)
    if source_hash != prior["source_video_sha256_by_game"]["PREL000102"]:
        raise ValueError("China source mismatch")
    if (prior["house_detector_sha256"] != digest(ROOT / "prototype/video_board_observation_v2.py")
            or prior["stone_detector_sha256"] != digest(ROOT / "prototype/video_board_observation.py")
            or prior["temporal_cluster_sha256"] != digest(ROOT / "prototype/temporal_board_state.py")):
        raise ValueError("Board detector changed after prior source-only scan")
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    if source_hash == reserved["source_sha256"]:
        raise ValueError("Reserved independent source is not development data")
    previous = [row for row in prior["rows"]
                if row["official_game_code"] == "PREL000102"]
    if len(previous) != 5 or {row["inferred_recording_delivery_side"]
                              for row in previous} != {"top"}:
        raise ValueError("Frozen recording orientation changed")
    game = next(row for row in alignment["games"]
                if row["official_game_code"] == "PREL000102")
    counters = sorted(game["counter_rows"], key=lambda row: row["counter_time_s"])
    chosen = [row for row in counters
              if row["official_shot_id"] in {
                  f"PREL000102-E02-S{number:02d}" for number in SHOT_NUMBERS}
              and row["status"] == "unique_colour_concordant"]
    if len(chosen) != len(SHOT_NUMBERS):
        raise ValueError("Predeclared adjacent counter anchors changed")
    capture = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG,
                               [cv2.CAP_PROP_N_THREADS, 1])
    fps = capture.get(cv2.CAP_PROP_FPS)
    rows = []
    for counter in chosen:
        anchor = counter["counter_time_s"]
        following = min((row["counter_time_s"] for row in counters
                         if row["counter_time_s"] > anchor), default=None)
        offsets = [offset for offset in OFFSETS_S
                   if following is None or anchor + offset <= following - 12]
        observations = []
        for offset in offsets:
            t = anchor + offset
            capture.set(cv2.CAP_PROP_POS_FRAMES, round(t * fps))
            ok, frame = capture.read()
            if not ok:
                raise RuntimeError(f"Decode failed at {t}")
            frame = cv2.resize(frame, (640, 360))
            house = detect_overhead_house(frame)
            if house is None:
                continue
            house = dict(house)
            if house["delivery_side"] == "uncertain":
                house["delivery_side"] = "top"
            if house["delivery_side"] != "top":
                continue
            observations.append({"time_s": t, "offset_s": offset,
                                 "house": house,
                                 "stones": detect_board_stones(frame, house)})
        stable = stable_board_stones(observations)
        rows.append({
            "shot_id": counter["official_shot_id"],
            "counter_id": counter["counter_id"],
            "counter_anchor_s": anchor,
            "following_counter_s": following,
            "sampled_offsets_s": offsets,
            "accepted_frame_count": len(observations),
            "frame_observations": observations,
            "stable_partial_board": stable,
        })
        print(rows[-1]["shot_id"], len(observations), len(stable), flush=True)
    capture.release()
    output = {
        "status": "source_pixel_adjacent_board_first_crossrecording_transfer_before_diagram_comparison",
        "source_sha256": source_hash,
        "counter_alignment_sha256": digest(ALIGNMENT),
        "prior_board_audit_sha256": digest(PRIOR),
        "house_detector_sha256": digest(ROOT / "prototype/video_board_observation_v2.py"),
        "stone_detector_sha256": digest(ROOT / "prototype/video_board_observation.py"),
        "temporal_cluster_sha256": digest(ROOT / "prototype/temporal_board_state.py"),
        "runner_sha256": digest(Path(__file__)),
        "selected_shot_numbers": list(SHOT_NUMBERS),
        "rows": rows,
        "limitations": [
            "Shot selection uses exposed development-source counter alignment.",
            "No official board positions enter frame selection or temporal clustering.",
            "A repeated visible stone is only a partial anonymous board observation.",
            "Counter timing is delayed and may not bracket the physical settle time.",
        ],
    }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n")


if __name__ == "__main__":
    main()
