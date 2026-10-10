"""Source-only held-to-motion cue over every provisional Slovakia event window."""

from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.origin_release_passage import scan_origin_release

UNION = ROOT / "validation/official-shot-sequence/pwg2022-provisional-event-evidence-union-development.json"
VIDEO = ROOT / "validation/throw-event-benchmark/paralympics-2022-slovakia-usa/source.mp4"
OUTPUT = ROOT / "validation/official-shot-sequence/slovakia-provisional-release-coverage-development.json"


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def build():
    union = json.loads(UNION.read_text())
    game = next(row for row in union["games"]
                if row["official_game_code"] == "PREL000103")
    source_hash = digest(VIDEO)
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    if source_hash != game["source_sha256"] or source_hash == reserved["source_sha256"]:
        raise ValueError("Source mismatch or reserved video")
    events = game["events"]
    if len({event["event_id"] for event in events}) != len(events):
        raise ValueError("Duplicate event ID")
    capture = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG,
                               [cv2.CAP_PROP_N_THREADS, 1])
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
        rows.append({
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
            "colour_relation": ("no_unique_passage" if colour is None else
                                "ledger_colour_unknown" if ledger_colour is None else
                                "agrees_with_ledger" if colour == ledger_colour else
                                "conflicts_with_ledger"),
            "physical_stone_identity_verified": False,
            "simulation_ready": False,
        })
        if index % 10 == 0:
            print(f"Scanned {index}/{len(events)}", flush=True)
    capture.release()
    return {
        "status": "development_all_provisional_slovakia_event_release_cue_coverage",
        "source_sha256": source_hash,
        "union_sha256": digest(UNION),
        "release_code_sha256": digest(ROOT / "prototype/origin_release_passage.py"),
        "cap_code_sha256": digest(ROOT / "prototype/stone_motion_fallback.py"),
        "runner_sha256": digest(Path(__file__)),
        "provisional_event_count": len(rows),
        "unique_passage_event_count": sum(row["unique_release_cue_s"] is not None
                                          for row in rows),
        "colour_conflict_count": sum(row["colour_relation"] == "conflicts_with_ledger"
                                     for row in rows),
        "rows": rows,
        "limitations": [
            "The scan covers existing provisional event windows, not all camera shots or all physical throws.",
            "The held-to-motion cue is unchanged from exposed 2022 development, and no independent labels assess its precision or recall.",
            "A cap passage within one view does not prove delivery identity across a broadcast cut or settle position.",
            "No event candidate, counter link, exact physical release, or simulation-ready state is promoted.",
        ],
    }


def main():
    payload = json.dumps(build(), indent=2) + "\n"
    if OUTPUT.exists():
        if OUTPUT.read_text() != payload:
            raise SystemExit("Existing full-candidate release audit differs from inputs or code")
        print(f"Verified {OUTPUT}")
    else:
        OUTPUT.write_text(payload)
        print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
