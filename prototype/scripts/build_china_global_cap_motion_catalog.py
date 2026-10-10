"""Transfer the frozen Norway 1 Hz shot-scoped cap scan to Canada–China."""

from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from prototype.scripts.build_norway_global_cap_motion_catalog import tracks_for_shot
from prototype.stone_motion_fallback import stone_cap_candidates


VIDEO = ROOT / "validation/throw-event-benchmark/paralympics-2022-canada-china/source.mp4"
MANIFEST = ROOT / "validation/curlobserver-learned-probe/china-full-transfer/shot-review/manifest.json"
OUTPUT = ROOT / "validation/official-shot-sequence/china-global-shot-scoped-cap-motion-first.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first China global cap catalog")
    manifest = json.loads(MANIFEST.read_text())
    video_hash = digest(VIDEO)
    if manifest["source_sha256"] != video_hash:
        raise SystemExit("Video does not match China shot manifest")
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
        raise RuntimeError("Cannot open China video")
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
        "shared_shot_track_code_sha256": digest(ROOT / "prototype/scripts/build_norway_global_cap_motion_catalog.py"),
        "runner_sha256": digest(Path(__file__)),
        "sample_rate_hz": 1,
        "sample_count": sample_count,
        "camera_shot_count": len(shots),
        "episode_count": sum(len(row["tracks"]) for row in rows),
        "selection_rule": "Full 0–8356 s source at integer seconds; identical Norway narrow red/yellow cap rule; tracks linked only within manifest camera shots.",
        "shots": rows,
        "limitations": [
            "A cap track may be an old stone, replay, adjacent sheet, graphic, or other movement; it is not a verified throw.",
            "One physical stone may produce several tracks across cuts, occlusions, or within-shot interruptions.",
            "The 1 Hz narrow cap rule can miss real stones and short motion.",
            "The shot manifest is development evidence, not independent physical event labels.",
        ],
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print({"camera_shots": len(rows), "episodes": result["episode_count"]})


if __name__ == "__main__":
    main()
