"""Scan the full Norway source once for narrow cap tracks within camera shots."""

from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from prototype.stone_motion_fallback import moving_cap_tracks, stone_cap_candidates


VIDEO = ROOT / "validation/throw-event-benchmark/paralympics-2022-canada-norway/source.mp4"
MANIFEST = ROOT / "validation/curlobserver-learned-probe/canada-norway-full-transfer/shot-review/manifest.json"
OUTPUT = ROOT / "validation/official-shot-sequence/norway-global-shot-scoped-cap-motion-first.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def summary(track, shot_id, colour, ordinal):
    points = track["points"]
    return {
        "episode_id": f"{shot_id}-{colour[0].upper()}{ordinal:02}",
        "camera_shot_id": shot_id,
        "colour": colour,
        "interval_s": [points[0]["time_s"], points[-1]["time_s"]],
        "span_px": round(track["span_px"], 2),
        "point_count": len(points),
        "first_pixel": points[0]["pixel"],
        "last_pixel": points[-1]["pixel"],
        "physical_stone_identity_verified": False,
    }


def tracks_for_shot(observations, shot_id):
    rows = []
    for colour in ("red", "yellow"):
        tracks = moving_cap_tracks(observations[colour])
        rows.extend(summary(track, shot_id, colour, i)
                    for i, track in enumerate(tracks, 1))
    return rows


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first global motion catalog")
    manifest = json.loads(MANIFEST.read_text())
    video_hash = digest(VIDEO)
    if manifest["source_sha256"] != video_hash:
        raise SystemExit("Video does not match shot manifest")
    shots = manifest["shots"]
    if not shots or shots[0]["interval_s"][0] != 0:
        raise SystemExit("Missing start of camera-shot coverage")
    if shots[-1]["interval_s"][1] != manifest["source_interval_s"][1]:
        raise SystemExit("Missing end of camera-shot coverage")
    if any(left["interval_s"][1] != right["interval_s"][0]
           for left, right in zip(shots, shots[1:])):
        raise SystemExit("Camera-shot manifest is not contiguous")
    cap = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        raise RuntimeError("Cannot open Norway video")
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        raise RuntimeError("Invalid video FPS")
    rows = []
    observations = {"red": [], "yellow": []}
    shot_index = 0
    sample_count = 0
    try:
        for second in range(int(manifest["source_interval_s"][1])):
            while shot_index + 1 < len(shots) and second >= shots[shot_index]["interval_s"][1]:
                shot = shots[shot_index]
                rows.append({"camera_shot_id": shot["id"], "interval_s": shot["interval_s"],
                             "tracks": tracks_for_shot(observations, shot["id"])})
                observations = {"red": [], "yellow": []}
                shot_index += 1
            cap.set(cv2.CAP_PROP_POS_FRAMES, round(second * fps))
            ok, frame = cap.read()
            if not ok:
                raise RuntimeError(f"Frame decode failed at {second}s")
            for colour in observations:
                observations[colour].append((float(second), stone_cap_candidates(frame, colour)))
            sample_count += 1
            if sample_count % 1000 == 0:
                print(f"sampled {sample_count}s/{manifest['source_interval_s'][1]}s", flush=True)
    finally:
        cap.release()
    shot = shots[shot_index]
    rows.append({"camera_shot_id": shot["id"], "interval_s": shot["interval_s"],
                 "tracks": tracks_for_shot(observations, shot["id"])})
    for remaining in shots[shot_index + 1:]:
        rows.append({"camera_shot_id": remaining["id"], "interval_s": remaining["interval_s"],
                     "tracks": []})
    if len(rows) != len(shots) or len({track["episode_id"] for row in rows for track in row["tracks"]}) != sum(len(row["tracks"]) for row in rows):
        raise RuntimeError("Shot or episode identity invariant failed")
    result = {
        "status": "source_only_global_1hz_shot_scoped_cap_motion_catalog_not_throw_events",
        "source_video_sha256": video_hash,
        "shot_manifest_sha256": digest(MANIFEST),
        "motion_detector_sha256": digest(ROOT / "prototype/stone_motion_fallback.py"),
        "runner_sha256": digest(Path(__file__)),
        "sample_rate_hz": 1,
        "sample_count": sample_count,
        "camera_shot_count": len(shots),
        "episode_count": sum(len(row["tracks"]) for row in rows),
        "selection_rule": "Full 0–9039 s source at integer seconds; narrow frozen red/yellow cap rule; tracks linked only within manifest camera shots.",
        "shots": rows,
        "limitations": [
            "A cap track may be an old stone, an adjacent sheet, a graphic, or other movement; it is not a verified throw.",
            "One physical stone may produce several tracks across cuts, occlusions, or within-shot interruptions.",
            "The 1 Hz narrow cap rule can miss real stones and short motion.",
            "The shot manifest is development evidence, not independent physical event labels.",
        ],
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print({"camera_shots": len(rows), "episodes": result["episode_count"]})


if __name__ == "__main__":
    main()
