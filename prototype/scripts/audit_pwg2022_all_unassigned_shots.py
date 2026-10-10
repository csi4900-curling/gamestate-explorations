"""Scan every camera shot unused by the additive v2 event union for release cues."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.origin_release_ice_support import passage_has_ice
from prototype.origin_release_passage import scan_origin_release

BASE = ROOT / "validation/official-shot-sequence"
UNION = BASE / "pwg2022-provisional-event-evidence-union-v2-source-rescues-development.json"
SOURCES = {
    "PREL000101": (
        ROOT / "validation/curlobserver-learned-probe/swiss-full-transfer/shot-origin.json",
        ROOT / "validation/throw-event-benchmark/paralympics-2022-sweden-switzerland/source.mp4"),
    "PREL000102": (
        ROOT / "validation/curlobserver-learned-probe/china-full-transfer/unlabelled-shot-origin-inference.json",
        ROOT / "validation/throw-event-benchmark/paralympics-2022-canada-china/source.mp4"),
    "PREL000103": (
        ROOT / "validation/curlobserver-learned-probe/slovakia-full-transfer/shot-origin.json",
        ROOT / "validation/throw-event-benchmark/paralympics-2022-slovakia-usa/source.mp4"),
}
PLAN = BASE / "pwg2022-all-unassigned-shots-source-scan-plan.json"
OUTPUTS = {code: BASE / f"pwg2022-all-unassigned-shots-{code}-source-scan-development.json"
           for code in SOURCES}


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def build_plan():
    union = json.loads(UNION.read_text())
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    games = []
    for game in union["games"]:
        code = game["official_game_code"]
        origin_path, video = SOURCES[code]
        origins = json.loads(origin_path.read_text())
        source_hash = digest(video)
        if (source_hash != game["source_sha256"] or
                source_hash != origins["source_sha256"] or
                source_hash == reserved["source_sha256"]):
            raise ValueError("Source mismatch or reserved-source overlap")
        assigned = {shot for event in game["events"] for shot in event["source_shot_ids"]}
        selected = [{"shot_id": row["shot_id"], "interval_s": row["interval_s"],
                     "origin_model_predicted": bool(row["predicted"]),
                     "origin_probability": row["probability"]}
                    for row in origins["rows"] if row["shot_id"] not in assigned]
        games.append({"recording_code": code, "source_sha256": source_hash,
                      "origin_sha256": digest(origin_path),
                      "unassigned_shot_count": len(selected), "selected_shots": selected})
    return {"status": "frozen_all_unassigned_camera_shots_not_negative_labels",
            "selection_rule": "Every source camera shot not named by any candidate in the additive v2 union, irrespective of origin-model prediction or counter proximity.",
            "union_sha256": digest(UNION),
            "release_code_sha256": digest(ROOT / "prototype/origin_release_passage.py"),
            "ice_code_sha256": digest(ROOT / "prototype/origin_release_ice_support.py"),
            "runner_sha256": digest(Path(__file__)),
            "total_unassigned_shot_count": sum(g["unassigned_shot_count"] for g in games),
            "games": games}


def scan_game(game):
    code = game["recording_code"]
    video = SOURCES[code][1]
    if digest(video) != game["source_sha256"]:
        raise ValueError("Source changed after selection freeze")
    capture = cv2.VideoCapture(str(video), cv2.CAP_FFMPEG,
                               [cv2.CAP_PROP_N_THREADS, 1])
    if not capture.isOpened():
        raise RuntimeError("Cannot open source video")
    rows = []
    try:
        fps = capture.get(cv2.CAP_PROP_FPS)
        for index, shot in enumerate(game["selected_shots"], 1):
            result = scan_origin_release(capture, fps, *shot["interval_s"])
            supported, rejected = [], []
            for passage in result["passages"]:
                held_time = passage["held_interval_s"][0]
                capture.set(cv2.CAP_PROP_POS_FRAMES, round(held_time * fps))
                ok, frame = capture.read()
                if not ok:
                    raise RuntimeError(f"Frame decode failed at {held_time}")
                ice, fraction = passage_has_ice(frame, passage)
                item = {**passage, "held_frame_time_s": held_time,
                        "below_ice_fraction": fraction}
                (supported if ice else rejected).append(item)
            rows.append({**shot,
                         "sampled_frame_count": result["sampled_frame_count"],
                         "filtered_cap_observation_count":
                         result["filtered_cap_observation_count"],
                         "raw_passages": result["passages"],
                         "ice_supported_passages": supported,
                         "ice_rejected_passages": rejected,
                         "unique_ice_supported_colour": supported[0]["colour"]
                         if len(supported) == 1 else None})
            if index % 25 == 0:
                print(f"{code}: {index}/{len(game['selected_shots'])}", flush=True)
    finally:
        capture.release()
    return {"status": "development_full_unassigned_shot_source_scan_not_event_f1",
            "recording_code": code, "source_sha256": game["source_sha256"],
            "plan_sha256": digest(PLAN), "scanned_shot_count": len(rows),
            "origin_predicted_shot_count": sum(row["origin_model_predicted"] for row in rows),
            "raw_passage_shot_count": sum(bool(row["raw_passages"]) for row in rows),
            "ice_supported_shot_count": sum(bool(row["ice_supported_passages"])
                                            for row in rows),
            "unique_ice_supported_shot_count": sum(
                row["unique_ice_supported_colour"] is not None for row in rows),
            "rows": rows,
            "limitations": [
                "Unassigned camera shots are not physical no-throw labels; some may belong to existing events or missed throws.",
                "The source-only cue has fixed geometry and can miss deliveries outside its corridor.",
                "No receiving-view identity or independent physical event F1 is inferred from this scan.",
            ]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("game_code", choices=sorted(SOURCES))
    args = parser.parse_args()
    plan = build_plan()
    payload = json.dumps(plan, indent=2) + "\n"
    if PLAN.exists() and PLAN.read_text() != payload:
        raise SystemExit("Frozen all-unassigned selection changed")
    if not PLAN.exists():
        PLAN.write_text(payload)
        print(f"Froze {PLAN}: {plan['total_unassigned_shot_count']} shots", flush=True)
    output = OUTPUTS[args.game_code]
    if output.exists():
        raise SystemExit("First scan exists; preserve it and verify separately")
    game = next(g for g in plan["games"] if g["recording_code"] == args.game_code)
    result = scan_game(game)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print({key: result[key] for key in ("scanned_shot_count", "raw_passage_shot_count",
                                       "unique_ice_supported_shot_count")})


if __name__ == "__main__":
    main()
