"""Apply unchanged within-view release cue to all ambiguous Slovakia options."""

from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.origin_release_passage import scan_origin_release

ALIGNMENT = ROOT / "validation/curlobserver-learned-probe/slovakia-full-transfer/counter-cap.json"
VIDEO = ROOT / "validation/throw-event-benchmark/paralympics-2022-slovakia-usa/source.mp4"
OUTPUT = (
    ROOT / "validation/official-shot-sequence/slovakia-ambiguous-release-passages-development.json"
)


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def build():
    alignment = json.loads(ALIGNMENT.read_text())
    source_hash = digest(VIDEO)
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    if source_hash != alignment["source_sha256"] or source_hash == reserved["source_sha256"]:
        raise ValueError("Source mismatch or reserved video")
    ambiguous = [
        row
        for row in alignment["rows"]
        if row["shot_id"] is None and len(row["candidate_shots"]) >= 2
    ]
    shots = {}
    for counter in ambiguous:
        for option in counter["candidate_shots"]:
            shot_id = option["shot_id"]
            if shot_id in shots and shots[shot_id] != option["interval_s"]:
                raise ValueError(f"Conflicting interval for {shot_id}")
            shots[shot_id] = option["interval_s"]
    capture = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not capture.isOpened():
        raise RuntimeError("Cannot open source video")
    fps = capture.get(cv2.CAP_PROP_FPS)
    rows = []
    for shot_id, interval in sorted(shots.items(), key=lambda item: int(item[0][1:])):
        result = scan_origin_release(capture, fps, *interval)
        passages = result["passages"]
        rows.append(
            {
                "shot_id": shot_id,
                "interval_s": interval,
                **result,
                "unique_passage_colour": passages[0]["colour"] if len(passages) == 1 else None,
            }
        )
    capture.release()
    by_shot = {row["shot_id"]: row for row in rows}
    counters = []
    for counter in ambiguous:
        options = []
        for option in counter["candidate_shots"]:
            shot = by_shot[option["shot_id"]]
            colour = shot["unique_passage_colour"]
            options.append(
                {
                    "shot_id": option["shot_id"],
                    "origin_probability": option["origin_probability"],
                    "unique_passage_colour": colour,
                    "passage_relation": (
                        "absent_or_ambiguous"
                        if colour is None
                        else "matches_counter"
                        if colour == counter["colour"]
                        else "conflicts_counter"
                    ),
                }
            )
        counters.append(
            {
                "counter_id": counter["counter_id"],
                "counter_colour": counter["colour"],
                "options": options,
            }
        )
    return {
        "status": "development_unchanged_release_cue_on_ambiguous_slovakia_options",
        "source_sha256": source_hash,
        "alignment_sha256": digest(ALIGNMENT),
        "release_code_sha256": digest(ROOT / "prototype/origin_release_passage.py"),
        "cap_code_sha256": digest(ROOT / "prototype/stone_motion_fallback.py"),
        "runner_sha256": digest(Path(__file__)),
        "selected_counter_count": len(ambiguous),
        "unique_candidate_shot_count": len(rows),
        "shot_rows": rows,
        "counter_rows": counters,
        "limitations": [
            "The 13 options were selected from exposed ambiguous counters; this is development, not full-match release recall.",
            "The release cue is source-only and unchanged, but its thresholds came from earlier exposed 2022 development.",
            "A within-view cap passage may still be equipment or the wrong stone; it does not establish cross-view identity or settle time.",
            "No counter or event ledger is modified, and no independent physical throw F1 is measured.",
        ],
    }


def main():
    payload = json.dumps(build(), indent=2) + "\n"
    if OUTPUT.exists():
        if OUTPUT.read_text() != payload:
            raise SystemExit("Existing passage audit differs from inputs or code")
        print(f"Verified {OUTPUT}")
    else:
        OUTPUT.write_text(payload)
        print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
