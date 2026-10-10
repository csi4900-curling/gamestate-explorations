"""Probe held-to-motion cues in origin-predicted shots absent from the event union."""

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
UNION = BASE / "pwg2022-provisional-event-evidence-union-development.json"
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
PLAN = BASE / "pwg2022-origin-shots-outside-union-plan.json"
OUTPUT = BASE / "pwg2022-origin-shots-outside-union-cues-development.json"


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def selection():
    union = json.loads(UNION.read_text())
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    games = []
    for game in union["games"]:
        code = game["official_game_code"]
        origins_path, video = SOURCES[code]
        origins = json.loads(origins_path.read_text())
        source_hash = digest(video)
        if (source_hash != game["source_sha256"] or
                source_hash != origins["source_sha256"] or
                source_hash == reserved["source_sha256"]):
            raise ValueError("Source mismatch or reserved-source overlap")
        event_shot_ids = {sid for event in game["events"]
                          for sid in event["source_shot_ids"]}
        selected = [{"shot_id": shot["shot_id"], "interval_s": shot["interval_s"],
                     "origin_probability": shot["probability"]}
                    for shot in origins["rows"]
                    if shot["predicted"] == 1 and shot["shot_id"] not in event_shot_ids]
        games.append({"recording_code": code, "source_sha256": source_hash,
                      "shot_origin_sha256": digest(origins_path),
                      "predicted_origin_shots_outside_union": selected})
    return {"status": "frozen_source_only_discovery_probe_selection_not_negative_labels",
            "selection_rule": "All frozen origin-predicted camera shots absent from every provisional union event source_shot_ids; no counter or cue outcome selects shots.",
            "union_sha256": digest(UNION),
            "release_code_sha256": digest(ROOT / "prototype/origin_release_passage.py"),
            "ice_code_sha256": digest(ROOT / "prototype/origin_release_ice_support.py"),
            "runner_sha256": digest(Path(__file__)),
            "selected_shot_count": sum(len(g["predicted_origin_shots_outside_union"])
                                       for g in games), "games": games}


def scan(plan):
    games = []
    for game in plan["games"]:
        code = game["recording_code"]
        video = SOURCES[code][1]
        if digest(video) != game["source_sha256"]:
            raise ValueError("Source video changed after selection freeze")
        capture = cv2.VideoCapture(str(video), cv2.CAP_FFMPEG,
                                   [cv2.CAP_PROP_N_THREADS, 1])
        if not capture.isOpened():
            raise RuntimeError(f"Cannot open source {code}")
        rows = []
        try:
            fps = capture.get(cv2.CAP_PROP_FPS)
            for index, shot in enumerate(game["predicted_origin_shots_outside_union"], 1):
                result = scan_origin_release(capture, fps, *shot["interval_s"])
                accepted, rejected = [], []
                for passage in result["passages"]:
                    frame_time = passage["held_interval_s"][0]
                    capture.set(cv2.CAP_PROP_POS_FRAMES, round(frame_time * fps))
                    ok, frame = capture.read()
                    if not ok:
                        raise RuntimeError(f"Frame decode failed at {frame_time}")
                    supported, fraction = passage_has_ice(frame, passage)
                    item = {**passage, "held_frame_time_s": frame_time,
                            "below_ice_fraction": fraction}
                    (accepted if supported else rejected).append(item)
                rows.append({**shot, "sampled_frame_count": result["sampled_frame_count"],
                             "filtered_cap_observation_count":
                             result["filtered_cap_observation_count"],
                             "raw_passages": result["passages"],
                             "ice_supported_passages": accepted,
                             "ice_rejected_passages": rejected,
                             "unique_supported_colour": accepted[0]["colour"]
                             if len(accepted) == 1 else None})
                if index % 10 == 0:
                    print(f"{code}: {index}/{len(game['predicted_origin_shots_outside_union'])}",
                          flush=True)
        finally:
            capture.release()
        games.append({"recording_code": code, "source_sha256": game["source_sha256"],
                      "selected_shot_count": len(rows),
                      "raw_passage_shot_count": sum(bool(r["raw_passages"]) for r in rows),
                      "unique_ice_supported_shot_count": sum(
                          r["unique_supported_colour"] is not None for r in rows),
                      "rows": rows})
    return {"status": "development_outside_union_origin_shot_discovery_probe_not_event_precision",
            "plan_sha256": digest(PLAN),
            "selected_shot_count": sum(g["selected_shot_count"] for g in games),
            "raw_passage_shot_count": sum(g["raw_passage_shot_count"] for g in games),
            "unique_ice_supported_shot_count": sum(
                g["unique_ice_supported_shot_count"] for g in games),
            "games": games,
            "limitations": [
                "Shots outside the provisional union are not independently labeled negatives; they may contain missed physical throws.",
                "The same rule is used without tuning on these windows, but the recordings are exposed development sources.",
                "A held-cap passage can be equipment or a non-delivered stone; physical event precision and recall remain unknown.",
            ]}


def main():
    selected = selection()
    frozen = json.dumps(selected, indent=2) + "\n"
    if PLAN.exists() and PLAN.read_text() != frozen:
        raise SystemExit("Frozen selection differs from inputs or code")
    if not PLAN.exists():
        PLAN.write_text(frozen)
        print(f"Froze {PLAN} with {selected['selected_shot_count']} shots", flush=True)
    if OUTPUT.exists():
        raise SystemExit("Output already exists; preserve first scan")
    result = scan(selected)
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print({key: result[key] for key in ("selected_shot_count", "raw_passage_shot_count",
                                       "unique_ice_supported_shot_count")})


if __name__ == "__main__":
    main()
