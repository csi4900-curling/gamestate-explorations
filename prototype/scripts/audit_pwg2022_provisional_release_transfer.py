"""Frozen first source-only release-cue transfer to Swiss and China ledgers."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.origin_release_passage import scan_origin_release

UNION = (
    ROOT
    / "validation/official-shot-sequence/pwg2022-provisional-event-evidence-union-development.json"
)
PLAN = ROOT / "validation/official-shot-sequence/pwg2022-provisional-release-transfer-plan.json"
VIDEOS = {
    "PREL000101": ROOT
    / "validation/throw-event-benchmark/paralympics-2022-sweden-switzerland/source.mp4",
    "PREL000102": ROOT
    / "validation/throw-event-benchmark/paralympics-2022-canada-china/source.mp4",
}
OUTPUTS = {
    "PREL000101": ROOT
    / "validation/official-shot-sequence/swiss-provisional-release-transfer-first.json",
    "PREL000102": ROOT
    / "validation/official-shot-sequence/china-provisional-release-transfer-first.json",
}


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def build(code):
    plan = json.loads(PLAN.read_text())
    if code not in VIDEOS or code not in plan["games"]:
        raise ValueError(f"Game not in frozen plan: {code}")
    for key, path in (
        ("union_sha256", UNION),
        ("release_code_sha256", ROOT / "prototype/origin_release_passage.py"),
        ("cap_code_sha256", ROOT / "prototype/stone_motion_fallback.py"),
        ("runner_sha256", Path(__file__)),
    ):
        if plan[key] != digest(path):
            raise ValueError(f"Frozen plan code/input mismatch: {key}")
    union = json.loads(UNION.read_text())
    game = next(row for row in union["games"] if row["official_game_code"] == code)
    video = VIDEOS[code]
    source_hash = digest(video)
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    if (
        source_hash != game["source_sha256"]
        or source_hash != plan["games"][code]["source_sha256"]
        or source_hash == reserved["source_sha256"]
        or len(game["events"]) != plan["games"][code]["expected_provisional_event_count"]
    ):
        raise ValueError("Source or selection differs from frozen plan")
    events = game["events"]
    if len({row["event_id"] for row in events}) != len(events):
        raise ValueError("Duplicate event ID")
    capture = cv2.VideoCapture(str(video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not capture.isOpened():
        raise RuntimeError("Cannot open source video")
    fps = capture.get(cv2.CAP_PROP_FPS)
    rows = []
    for index, event in enumerate(events, 1):
        interval = event["delivery_window_s"]
        if interval is None:
            raise ValueError(f"Missing delivery window: {event['event_id']}")
        result = scan_origin_release(capture, fps, *interval)
        passages = result["passages"]
        unique = passages[0] if len(passages) == 1 else None
        colour = unique["colour"] if unique else None
        ledger_colour = event["colour"]
        rows.append(
            {
                "event_id": event["event_id"],
                "source_shot_ids": event["source_shot_ids"],
                "delivery_window_s": interval,
                "counter_id": event["counter_id"],
                "ledger_colour": ledger_colour,
                "ledger_colour_status": event["colour_status"],
                "sampled_frame_count": result["sampled_frame_count"],
                "filtered_cap_observation_count": result["filtered_cap_observation_count"],
                "passages": passages,
                "unique_passage_colour": colour,
                "unique_release_cue_s": unique["release_cue_s"] if unique else None,
                "colour_relation": (
                    "no_unique_passage"
                    if colour is None
                    else "ledger_colour_unknown"
                    if ledger_colour is None
                    else "agrees_with_ledger"
                    if colour == ledger_colour
                    else "conflicts_with_ledger"
                ),
                "physical_stone_identity_verified": False,
                "simulation_ready": False,
            }
        )
        if index % 10 == 0:
            print(f"{code}: scanned {index}/{len(events)}", flush=True)
    capture.release()
    return {
        "status": "frozen_first_source_only_release_cue_transfer_not_event_f1",
        "recording_code": code,
        "source_sha256": source_hash,
        "frozen_plan_sha256": digest(PLAN),
        "union_sha256": digest(UNION),
        "release_code_sha256": digest(ROOT / "prototype/origin_release_passage.py"),
        "cap_code_sha256": digest(ROOT / "prototype/stone_motion_fallback.py"),
        "runner_sha256": digest(Path(__file__)),
        "provisional_event_count": len(rows),
        "unique_passage_event_count": sum(row["unique_release_cue_s"] is not None for row in rows),
        "colour_conflict_count": sum(
            row["colour_relation"] == "conflicts_with_ledger" for row in rows
        ),
        "rows": rows,
        "limitations": [
            "The same cue and all union candidate windows were frozen before these two runs; neither is an independent physical event label set.",
            "Scanning provisional candidates does not measure full-video throw recall or event F1.",
            "A within-view cap passage may be a different stone or equipment and does not establish cross-cut identity or settle position.",
            "No event ledger, counter link, exact physical release, or simulation-ready state is promoted.",
        ],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("game_code", choices=sorted(VIDEOS))
    args = parser.parse_args()
    output = OUTPUTS[args.game_code]
    payload = json.dumps(build(args.game_code), indent=2) + "\n"
    if output.exists():
        if output.read_text() != payload:
            raise SystemExit("Existing first-transfer output differs from frozen inputs")
        print(f"Verified {output}")
    else:
        output.write_text(payload)
        print(f"Wrote {output}")


if __name__ == "__main__":
    main()
