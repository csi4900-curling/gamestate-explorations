"""First source-only end-4 transfer of the frozen short-cap-transit cue."""

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
from short_cap_transit import short_transits
from stone_motion_fallback import stone_cap_candidates
from stone_patch_detector import load_model

BASE = ROOT / "validation/curlobserver-learned-probe"
VIDEO = ROOT / "validation/throw-event-benchmark/paralympics-2022-canada-norway/source.mp4"
SHOTS = BASE / "canada-norway-full-transfer/cap-motion.json"
MODEL = BASE / "cap-patch-crossmatch-v1/model-excluding-swiss-transfer.npz"
FROZEN = BASE / "cap-patch-crossmatch-v1/norway-end2-short-transit.json"
OUTPUT = BASE / "cap-patch-crossmatch-v1/norway-end4-short-transit-first.json"
INTERVAL = (3207.5, 4187.0)


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve the first end-4 scan")
    source_hash = digest(VIDEO)
    manifest = json.loads(SHOTS.read_text())
    frozen = json.loads(FROZEN.read_text())
    first_window = json.loads(
        (BASE / "cap-patch-crossmatch-v1/norway-end2-targeted-transfer.json").read_text()
    )
    if manifest["source_sha256"] != source_hash or frozen["source_sha256"] != source_hash:
        raise ValueError("Source mismatch")
    if frozen["motion_code_sha256"] != digest(ROOT / "prototype/short_cap_transit.py"):
        raise ValueError("Short-transit rule changed after the end-2 diagnostic")
    if first_window["model_sha256"] != digest(MODEL):
        raise ValueError("Cap verifier changed after the end-2 diagnostic")
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    if source_hash == reserved["source_sha256"]:
        raise ValueError("Reserved independent source is not development data")
    selected = [
        shot
        for shot in manifest["shots"]
        if INTERVAL[0] <= sum(shot["interval_s"]) / 2 < INTERVAL[1]
    ]
    if len(selected) != 73 or selected[0]["shot_id"] != "S234" or selected[-1]["shot_id"] != "S306":
        raise ValueError("Predeclared end-4 shot selection changed")
    model = load_model(MODEL)
    capture = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not capture.isOpened():
        raise ValueError("Cannot open source")
    fps = capture.get(cv2.CAP_PROP_FPS)
    step = round(fps / 5)
    if fps <= 0 or step < 1:
        raise ValueError("Invalid video rate")
    rows = []
    for shot in selected:
        start, end = shot["interval_s"]
        first_frame, last_frame = ceil(start * fps), ceil(end * fps)
        capture.set(cv2.CAP_PROP_POS_FRAMES, first_frame)
        observations = {colour: [] for colour in ("red", "yellow")}
        counts = Counter()
        for frame_index in range(first_frame, last_frame):
            if not capture.grab():
                raise RuntimeError(f"Decode failed at frame {frame_index}")
            if frame_index % step:
                continue
            ok, frame = capture.retrieve()
            if not ok:
                raise RuntimeError(f"Retrieve failed at frame {frame_index}")
            t = round(frame_index / fps, 3)
            for colour in observations:
                raw = stone_cap_candidates(
                    frame, colour, allow_bright_body=True, allow_large_caps=True
                )
                scored = score_candidates(frame, raw, model)
                observations[colour].append(
                    (t, [item for item in scored if item["patch_accepted"]])
                )
                counts[f"{colour}_raw"] += len(raw)
                counts[f"{colour}_accepted"] += sum(item["patch_accepted"] for item in scored)
            counts["frames"] += 1
        tracks = []
        for colour in observations:
            tracks.extend(dict(row, colour=colour) for row in short_transits(observations[colour]))
        tracks.sort(key=lambda row: (-row["point_count"], -row["displacement_px"]))
        rows.append(
            {
                "shot_id": shot["shot_id"],
                "interval_s": shot["interval_s"],
                "sampled_frames": counts["frames"],
                "candidate_counts": {
                    key: counts[key]
                    for key in ("red_raw", "red_accepted", "yellow_raw", "yellow_accepted")
                },
                "transits": tracks,
            }
        )
        if len(rows) % 8 == 0:
            print(f"Scanned {len(rows)}/{len(selected)} camera shots", flush=True)
    capture.release()
    result = {
        "status": "source_only_first_end4_short_cap_transit_not_event_score",
        "source_sha256": source_hash,
        "shot_manifest_sha256": digest(SHOTS),
        "model_sha256": digest(MODEL),
        "frozen_end2_diagnostic_sha256": digest(FROZEN),
        "motion_code_sha256": digest(ROOT / "prototype/short_cap_transit.py"),
        "patch_code_sha256": digest(ROOT / "prototype/cap_patch_verifier.py"),
        "runner_sha256": digest(Path(__file__)),
        "selection_interval_s": list(INTERVAL),
        "selection_rule": "All 73 camera-shot segments whose midpoint falls within the end-4 partition fixed by the prior sequence diagnostic; no counter or official colour used to select detections.",
        "sample_rate_hz": fps / step,
        "shot_count": len(rows),
        "shots_with_transit": sum(bool(row["transits"]) for row in rows),
        "transit_count": sum(len(row["transits"]) for row in rows),
        "rows": rows,
        "limitations": [
            "This transfers within the same exposed match and broadcast production; it is not independent event F1.",
            "The end partition is prior diagnostic context, not a deployable inference input.",
            "A short within-shot cap path is not a confirmed delivered stone or camera-handoff link.",
            "No official counter or shot order was read by the visual inference step.",
        ],
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print(
        {
            "shots": len(rows),
            "with_transit": result["shots_with_transit"],
            "transits": result["transit_count"],
        }
    )


if __name__ == "__main__":
    main()
