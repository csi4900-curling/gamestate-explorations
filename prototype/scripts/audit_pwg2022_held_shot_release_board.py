"""Rescan attached held-origin shots and join their release cues to partial boards."""

from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.origin_release_passage import scan_origin_release
from prototype.release_board_handoff import join_release_boards

BASE = ROOT / "validation/official-shot-sequence"
UNION = BASE / "pwg2022-provisional-event-evidence-union-development.json"
BOARDS = BASE / "pwg2022-provisional-event-board-evidence-v2.json"
OLD = BASE / "pwg2022-release-to-board-handoff-development.json"
RELEASES = {
    "PREL000101": BASE / "swiss-provisional-release-transfer-first.json",
    "PREL000102": BASE / "china-provisional-release-transfer-first.json",
    "PREL000103": BASE / "slovakia-provisional-release-coverage-development.json",
}
CHINA_SHOTS = (
    ROOT
    / "validation/curlobserver-learned-probe/china-full-transfer/unlabelled-shot-origin-inference.json"
)
CHINA_VIDEO = ROOT / "validation/throw-event-benchmark/paralympics-2022-canada-china/source.mp4"
OUTPUT = BASE / "pwg2022-held-shot-release-to-board-development.json"


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def build():
    union = json.loads(UNION.read_text())
    boards = json.loads(BOARDS.read_text())
    old = json.loads(OLD.read_text())
    releases = {code: json.loads(path.read_text()) for code, path in RELEASES.items()}
    shots = json.loads(CHINA_SHOTS.read_text())
    china = next(game for game in union["games"] if game["official_game_code"] == "PREL000102")
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    source_hash = digest(CHINA_VIDEO)
    if (
        source_hash != china["source_sha256"]
        or source_hash != shots["source_sha256"]
        or source_hash != releases["PREL000102"]["source_sha256"]
        or source_hash == reserved["source_sha256"]
    ):
        raise ValueError("China source hash mismatch or reserved-source overlap")
    shot_by_id = {row["shot_id"]: row for row in shots["rows"]}
    capture = cv2.VideoCapture(str(CHINA_VIDEO), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not capture.isOpened():
        raise RuntimeError("Cannot open China source video")
    scoped = []
    try:
        for event in china["events"]:
            held = event.get("attached_held_evidence")
            if event["candidate_class"] != "counter_linked_travel_only_provisional" or not held:
                continue
            shot = shot_by_id[held["shot_id"]]
            interval = shot["interval_s"]
            if (
                held["shot_id"] not in event["source_shot_ids"]
                or not interval[0] <= held["release_cue_s"] < interval[1]
            ):
                raise ValueError("Held cue is outside attached source shot")
            result = scan_origin_release(capture, capture.get(cv2.CAP_PROP_FPS), *interval)
            passages = result["passages"]
            cue = passages[0] if len(passages) == 1 else None
            if cue and cue["release_cue_s"] != held["release_cue_s"]:
                raise ValueError("Rescanned cue differs from attached held cue")
            original = next(
                row
                for row in releases["PREL000102"]["rows"]
                if row["event_id"] == event["event_id"]
            )
            original.update(
                {
                    "delivery_window_s": interval,
                    "sampled_frame_count": result["sampled_frame_count"],
                    "filtered_cap_observation_count": result["filtered_cap_observation_count"],
                    "passages": passages,
                    "unique_passage_colour": cue["colour"] if cue else None,
                    "unique_release_cue_s": cue["release_cue_s"] if cue else None,
                }
            )
            scoped.append(
                {
                    "event_id": event["event_id"],
                    "held_shot_id": held["shot_id"],
                    "held_shot_interval_s": interval,
                    "broad_window_s": event["delivery_window_s"],
                    "broad_passage_count": len(
                        next(
                            row
                            for row in json.loads(RELEASES["PREL000102"].read_text())["rows"]
                            if row["event_id"] == event["event_id"]
                        )["passages"]
                    ),
                    "scoped_scan": result,
                }
            )
    finally:
        capture.release()
    rows = join_release_boards(boards["links"], union["games"], list(releases.values()))
    if len(rows) != 9 or len(scoped) != 2:
        raise ValueError("Unexpected board or attached-held event count")
    changed = [
        row
        for row, previous in zip(rows, old["rows"])
        if row["release_cue_status"] != previous["release_cue_status"]
    ]
    if len(changed) != 1 or changed[0]["counter_id"] != "B57":
        raise ValueError("Unexpected change from broad-window handoff")
    return {
        "status": "development_scoped_held_shot_release_to_partial_board_not_physical_identity",
        "input_sha256": {
            "union": digest(UNION),
            "boards": digest(BOARDS),
            "broad_handoff": digest(OLD),
            "china_shots": digest(CHINA_SHOTS),
            "china_video": source_hash,
            "release_sidecars": {code: digest(path) for code, path in RELEASES.items()},
            "release_code": digest(ROOT / "prototype/origin_release_passage.py"),
            "join_code": digest(ROOT / "prototype/release_board_handoff.py"),
            "runner": digest(Path(__file__)),
        },
        "rescanned_held_origin_shots": scoped,
        "partial_board_count": len(rows),
        "unique_counter_linked_event_count": sum(
            row["event_join_status"] == "unique_shared_counter" for row in rows
        ),
        "boards_with_unique_within_view_release_cue": sum(
            row["release_cue_status"] == "cue_precedes_board" for row in rows
        ),
        "rows": rows,
        "limitations": [
            "The earlier broad-window 0/9 count remains a reproducible artifact, but B57 was ambiguous only because its scan crossed camera shots.",
            "The correction applies only to events with attached held-origin shots; other candidate windows retain their earlier scan status.",
            "A delayed-counter join plus matching cue colour and timing does not establish physical stone identity across views or a verified board transition.",
            "All boards are partial and uncalibrated; none is simulation-ready.",
        ],
    }


def main():
    payload = json.dumps(build(), indent=2) + "\n"
    if OUTPUT.exists() and OUTPUT.read_text() != payload:
        raise SystemExit("Existing scoped handoff differs from hashed inputs or code")
    if not OUTPUT.exists():
        OUTPUT.write_text(payload)
    print(f"Verified {OUTPUT}")


if __name__ == "__main__":
    main()
