"""Postscore raw held-cap diagnostic on all exposed end-6 origin shots."""

from hashlib import sha256
import json
from math import ceil
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cap_patch_verifier import score_candidates
from held_origin_cue import central_cap_candidates, summarize_held_origin
from stone_motion_fallback import stone_cap_candidates
from stone_patch_detector import load_model

BASE = ROOT / "validation/curlobserver-learned-probe/cap-patch-crossmatch-v1"
VIDEO = ROOT / "validation/throw-event-benchmark/paralympics-2022-canada-norway/source.mp4"
ROUTED = BASE / "norway-end6-dual-gate-events-first.json"
MODEL = BASE / "model-excluding-swiss-transfer.npz"
OUTPUT = BASE / "norway-end6-held-origin-development.json"


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first held-origin diagnostic")
    source_hash = digest(VIDEO)
    routed = json.loads(ROUTED.read_text())
    if routed["source_sha256"] != source_hash:
        raise ValueError("Source mismatch")
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    if source_hash == reserved["source_sha256"]:
        raise ValueError("Reserved independent source is not development data")
    model = load_model(MODEL)
    capture = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG,
                               [cv2.CAP_PROP_N_THREADS, 1])
    fps = capture.get(cv2.CAP_PROP_FPS)
    step = round(fps / 5)
    if fps <= 0 or step < 1:
        raise ValueError("Invalid source rate")
    rows = []
    for event in routed["decisions"]:
        start, stop = event["interval_s"]
        first, last = ceil(start * fps), ceil(stop * fps)
        capture.set(cv2.CAP_PROP_POS_FRAMES, first)
        observations = []
        for frame_index in range(first, last):
            if not capture.grab():
                raise RuntimeError(f"Decode failed at frame {frame_index}")
            if frame_index % step:
                continue
            ok, frame = capture.retrieve()
            if not ok:
                raise RuntimeError(f"Retrieve failed at frame {frame_index}")
            t = round(frame_index / fps, 3)
            candidates = []
            for colour in ("red", "yellow"):
                raw = stone_cap_candidates(frame, colour,
                                           allow_bright_body=True,
                                           allow_large_caps=True)
                scored = score_candidates(frame, raw, model)
                candidates.extend(dict(row, colour=colour)
                                  for row in central_cap_candidates(scored, event["side"]))
            observations.append((t, candidates))
        evidence = summarize_held_origin(observations)
        rows.append({"shot_id": event["shot_id"], "interval_s": event["interval_s"],
                     "side": event["side"], "sampled_frames": len(observations),
                     "evidence": evidence,
                     "samples": [{"time_s": t, "candidates": candidates}
                                 for t, candidates in observations]})
        if len(rows) % 5 == 0:
            print(f"Scanned {len(rows)}/{len(routed['decisions'])} origin shots", flush=True)
    capture.release()
    output = {
        "status": "postscore_exposed_end6_held_and_moving_cap_diagnostic",
        "source_sha256": source_hash,
        "routed_first_result_sha256": digest(ROUTED),
        "model_sha256": digest(MODEL),
        "cue_code_sha256": digest(ROOT / "prototype/held_origin_cue.py"),
        "runner_sha256": digest(Path(__file__)),
        "sample_rate_hz": fps / step,
        "selection": "All 20 origin-positive end-six shots and sides from their first source-only dual-gate result, rescanned after colour conflicts were inspected.",
        "rows": rows,
        "limitations": [
            "Central corridor and permissive patch score were chosen after viewing exposed end-six failures.",
            "A held cap does not establish release, delivery identity or cross-cut persistence.",
            "The side router itself was selected on earlier exposed ends and is not independently validated.",
        ],
    }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n")
    for row in rows:
        print(row["shot_id"], {colour: {
            "count": row["evidence"][colour]["candidate_count"],
            "hold_s": (row["evidence"][colour]["best_hold"] or {}).get("duration_s"),
            "motion_px": (row["evidence"][colour]["best_motion"] or {}).get("displacement_px")}
            for colour in ("red", "yellow")})


if __name__ == "__main__":
    main()
