"""Apply a frozen cross-match cap verifier to exposed Norway end-2 windows.

Selected windows use the earlier counter-proxy score. This is a development
diagnostic, not held-out event precision/recall.
"""

from collections import Counter
from hashlib import sha256
import json
from math import ceil
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cap_patch_verifier import score_candidates
from scripts.audit_full_shot_cap_motion import tracks_for_shot
from stone_motion_fallback import stone_cap_candidates
from stone_patch_detector import load_model

BASE = ROOT / "validation/throw-event-benchmark/paralympics-2022-canada-norway"
VIDEO = BASE / "source.mp4"
FIRST = BASE / "FIRST-TRANSFER.json"
CAP = ROOT / "validation/curlobserver-learned-probe/canada-norway-full-transfer/cap-motion.json"
MODEL = ROOT / "validation/curlobserver-learned-probe/cap-patch-crossmatch-v1/model-excluding-swiss-transfer.npz"
OUTPUT = ROOT / "validation/curlobserver-learned-probe/cap-patch-crossmatch-v1/norway-end2-targeted-transfer.json"
IDS = ("S93", "S95", "S97", "S99", "S115", "S129", "S139", "S156")


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first targeted verifier result")
    source_hash = digest(VIDEO)
    first = json.loads(FIRST.read_text())
    cap = json.loads(CAP.read_text())
    if first["source_video_sha256"] != source_hash or cap["source_sha256"] != source_hash:
        raise ValueError("Input source mismatch")
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    if source_hash == reserved["source_sha256"]:
        raise ValueError("Reserved independent source is not development data")
    prior = json.loads((MODEL.parent / "results.json").read_text())
    fold = next(row for row in prior["folds"] if row["heldout"] == "swiss-transfer")
    if fold["model_sha256"] != digest(MODEL):
        raise ValueError("Cap verifier differs from frozen cross-match fold")
    shots = {row["shot_id"]: row for row in cap["shots"]}
    score = first["complete_counter_anchored_ends"][0]["cap_only_score"]
    matches = {row["visual_id"]: row for row in score["matches"]}
    if not all(key in shots and key in matches for key in IDS):
        raise ValueError("Declared windows changed")
    model = load_model(MODEL)
    capture = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG,
                               [cv2.CAP_PROP_N_THREADS, 1])
    if not capture.isOpened():
        raise ValueError("Cannot open source")
    fps = capture.get(cv2.CAP_PROP_FPS)
    step = round(fps / 5)
    if fps <= 0 or step < 1:
        raise ValueError("Invalid video rate")
    rows = []
    for shot_id in IDS:
        interval = shots[shot_id]["interval_s"]
        first_frame, last_frame = ceil(interval[0] * fps), ceil(interval[1] * fps)
        capture.set(cv2.CAP_PROP_POS_FRAMES, first_frame)
        raw = {colour: [] for colour in ("red", "yellow")}
        filtered = {colour: [] for colour in ("red", "yellow")}
        totals = Counter()
        samples = []
        for frame_index in range(first_frame, last_frame):
            if not capture.grab():
                raise RuntimeError(f"Decode failed at frame {frame_index}")
            if frame_index % step:
                continue
            ok, frame = capture.retrieve()
            if not ok:
                raise RuntimeError(f"Retrieve failed at frame {frame_index}")
            t = round(frame_index / fps, 3)
            scores = {}
            for colour in ("red", "yellow"):
                proposals = stone_cap_candidates(frame, colour,
                                                 allow_bright_body=True,
                                                 allow_large_caps=True)
                scored = score_candidates(frame, proposals, model)
                raw[colour].append((t, scored))
                filtered[colour].append((t, [row for row in scored
                                             if row["patch_accepted"]]))
                totals[f"{colour}_raw"] += len(scored)
                totals[f"{colour}_accepted"] += sum(row["patch_accepted"] for row in scored)
                scores[colour] = scored
            samples.append({"time_s": t, "candidates": scores})
        raw_tracks = tracks_for_shot(raw, shot_id)
        filtered_tracks = tracks_for_shot(filtered, shot_id)
        old_tracks = shots[shot_id]["same_shot_candidates"]
        match = matches[shot_id]
        rows.append({
            "shot_id": shot_id, "interval_s": interval,
            "frozen_visual_colour": match["visual_colour"],
            "counter_proxy_colour": match["counter_colour"],
            "counter_pair_official_shot_id": match["official_shot_id"],
            "sampled_frame_count": len(samples),
            "candidate_counts": dict(totals),
            "original_frozen_cap_tracks": old_tracks,
            "rerun_raw_tracks": raw_tracks,
            "patch_filtered_tracks": filtered_tracks,
            "samples": samples,
        })
    capture.release()
    result = {
        "status": "exposed_development_targeted_cap_verifier_not_event_score",
        "source_sha256": source_hash,
        "first_transfer_sha256": digest(FIRST),
        "frozen_cap_motion_sha256": digest(CAP),
        "model_sha256": digest(MODEL),
        "cap_code_sha256": digest(ROOT / "prototype/stone_motion_fallback.py"),
        "patch_code_sha256": digest(ROOT / "prototype/cap_patch_verifier.py"),
        "runner_sha256": digest(Path(__file__)),
        "sample_rate_hz": fps / step,
        "selection": "Four prior end-2 colour conflicts and four agreement controls; frozen cap verifier trained on China and Slovakia samples, no Norway fitting.",
        "rows": rows,
        "limitations": [
            "Windows were selected after examining the first transfer; there is no independent event score.",
            "A broadcast counter colour is delayed and may be paired with the wrong visual window.",
            "The cap verifier was trained on small, developer-labelled patches from other Beijing broadcasts.",
            "Cap tracks are visual motion evidence, not delivered-stone identity or camera-handoff proof.",
        ],
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    for row in rows:
        print(row["shot_id"], row["counter_proxy_colour"],
              "raw", dict(Counter(t["colour"] for t in row["rerun_raw_tracks"])),
              "filtered", dict(Counter(t["colour"] for t in row["patch_filtered_tracks"])))


if __name__ == "__main__":
    main()
