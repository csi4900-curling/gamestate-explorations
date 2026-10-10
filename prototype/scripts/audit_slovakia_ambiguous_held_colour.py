"""Development transfer of held-cap colour to every Slovakia counter option."""

from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cap_patch_verifier import score_candidates
from held_origin_cue import central_cap_candidates, summarize_held_origin
from stone_motion_fallback import stone_cap_candidates
from stone_patch_detector import load_model

BASE = ROOT / "validation/curlobserver-learned-probe/slovakia-full-transfer"
ALIGNMENT = BASE / "counter-cap.json"
VIDEO = ROOT / "validation/throw-event-benchmark/paralympics-2022-slovakia-usa/source.mp4"
MODEL = ROOT / "validation/curlobserver-learned-probe/cap-patch-crossmatch-v1/model-excluding-slovakia-heldout.npz"
OUTPUT = ROOT / "validation/official-shot-sequence/slovakia-ambiguous-held-colour-development.json"


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def scan_shot(capture, fps, interval, model):
    observations = []
    for tick in range(round(interval[0] * 5), round(interval[1] * 5)):
        time_s = round(tick / 5, 3)
        capture.set(cv2.CAP_PROP_POS_FRAMES, round(time_s * fps))
        ok, frame = capture.read()
        if not ok:
            raise RuntimeError(f"Cannot decode {time_s}")
        candidates = []
        for colour in ("red", "yellow"):
            raw = stone_cap_candidates(frame, colour, allow_bright_body=True,
                                       allow_large_caps=True)
            scored = score_candidates(frame, raw, model)
            candidates.extend(dict(item, colour=colour) for item in
                              central_cap_candidates(scored, "right", minimum_score=0))
        observations.append((time_s, candidates))
    evidence = summarize_held_origin(observations)
    held_colours = [colour for colour in ("red", "yellow")
                    if evidence[colour]["best_hold"] is not None]
    return {"sampled_frame_count": len(observations),
            "candidate_count_by_colour": {colour: evidence[colour]["candidate_count"]
                                          for colour in ("red", "yellow")},
            "best_hold_by_colour": {colour: evidence[colour]["best_hold"]
                                    for colour in ("red", "yellow")},
            "unique_held_colour": held_colours[0] if len(held_colours) == 1 else None,
            "held_colour_status": "unique" if len(held_colours) == 1 else
                                  ("ambiguous" if held_colours else "absent")}


def build():
    alignment = json.loads(ALIGNMENT.read_text())
    video_hash = digest(VIDEO)
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    if video_hash != alignment["source_sha256"] or video_hash == reserved["source_sha256"]:
        raise ValueError("Source mismatch or reserved video")
    selected = [row for row in alignment["rows"]
                if row["shot_id"] is None and len(row["candidate_shots"]) >= 2]
    shots = {}
    for counter in selected:
        for option in counter["candidate_shots"]:
            shot_id = option["shot_id"]
            if shot_id in shots and shots[shot_id] != option["interval_s"]:
                raise ValueError(f"Conflicting interval: {shot_id}")
            shots[shot_id] = option["interval_s"]
    model = load_model(MODEL)
    capture = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG,
                               [cv2.CAP_PROP_N_THREADS, 1])
    if not capture.isOpened():
        raise RuntimeError("Cannot open source video")
    fps = capture.get(cv2.CAP_PROP_FPS)
    rows = []
    for shot_id, interval in sorted(shots.items(), key=lambda item: int(item[0][1:])):
        rows.append({"shot_id": shot_id, "interval_s": interval,
                     **scan_shot(capture, fps, interval, model)})
    capture.release()
    by_shot = {row["shot_id"]: row for row in rows}
    counters = []
    for counter in selected:
        options = [{"shot_id": option["shot_id"],
                    "origin_probability": option["origin_probability"],
                    "unique_held_colour": by_shot[option["shot_id"]]["unique_held_colour"],
                    "held_colour_status": by_shot[option["shot_id"]]["held_colour_status"],
                    "colour_relation": ("unknown" if by_shot[option["shot_id"]]["unique_held_colour"] is None
                                        else "matches_counter" if
                                        by_shot[option["shot_id"]]["unique_held_colour"] == counter["colour"]
                                        else "conflicts_counter")}
                   for option in counter["candidate_shots"]]
        counters.append({"counter_id": counter["counter_id"],
                         "counter_colour": counter["colour"],
                         "options": options})
    return {"status": "postscore_exposed_slovakia_ambiguous_held_colour_diagnostic",
            "source_sha256": video_hash,
            "alignment_sha256": digest(ALIGNMENT),
            "model_sha256": digest(MODEL),
            "code_sha256": digest(Path(__file__)),
            "cap_code_sha256": digest(ROOT / "prototype/stone_motion_fallback.py"),
            "held_cue_code_sha256": digest(ROOT / "prototype/held_origin_cue.py"),
            "selected_counter_count": len(selected),
            "unique_candidate_shot_count": len(rows),
            "shot_rows": rows,
            "counter_rows": counters,
            "limitations": [
                "Right-side delivery corridor was selected after inspecting S372 and S411; this is development, not independent transfer.",
                "The model excluded Slovakia from patch training, but the corridor and review selection were postscore.",
                "A held colour cap does not prove release or cross-view stone identity.",
                "No event ledger, counter association, or physical throw F1 changes.",
            ]}


def main():
    payload = json.dumps(build(), indent=2) + "\n"
    if OUTPUT.exists():
        if OUTPUT.read_text() != payload:
            raise SystemExit("Existing held-colour audit differs from inputs or code")
        print(f"Verified {OUTPUT}")
    else:
        OUTPUT.write_text(payload)
        print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
