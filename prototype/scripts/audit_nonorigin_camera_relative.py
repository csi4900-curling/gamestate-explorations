"""Camera-compensated motion audit of non-origin stone-cap candidates."""

from collections import defaultdict
from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from camera_relative_motion import sample_track_camera_motion
from held_origin_cue import _tracks

BASE = ROOT / "validation/curlobserver-learned-probe/cap-patch-crossmatch-v1"
INPUT = BASE / "nonorigin-cap-object-audit-development.json"
OUTPUT = BASE / "nonorigin-camera-relative-audit-development.json"
VIDEOS = {
    "norway": ROOT / "validation/throw-event-benchmark/paralympics-2022-canada-norway/source.mp4",
    "swiss": ROOT / "validation/throw-event-benchmark/paralympics-2022-sweden-switzerland/source.mp4",
}


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def selected_track(row):
    colour = row["candidate_colour"]
    evidence = row["evidence"][colour]
    if not evidence["transits"]:
        return None
    top = evidence["transits"][0]
    by_time = defaultdict(list)
    for sample in evidence["accepted_samples"]:
        by_time[sample["time_s"]].append(sample)
    matches = [track for track in _tracks(sorted(by_time.items()))
               if track[0]["time_s"] == top["interval_s"][0]
               and track[0]["pixel"] == top["first_pixel"]]
    if len(matches) != 1 or matches[0][-1]["time_s"] != top["interval_s"][1]:
        raise ValueError(f"Cannot recover frozen top track: {row['shot_id']}")
    return matches[0]


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first diagnostic")
    data = json.loads(INPUT.read_text())
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    sources = {name: digest(video) for name, video in VIDEOS.items()}
    if sources != data["source_sha256"] or reserved["source_sha256"] in sources.values():
        raise ValueError("Source hashes changed or reserved source selected")
    output_rows = []
    for row in data["rows"]:
        points = selected_track(row)
        capture = cv2.VideoCapture(str(VIDEOS[row["source"]]), cv2.CAP_FFMPEG,
                                   [cv2.CAP_PROP_N_THREADS, 1])
        fps = capture.get(cv2.CAP_PROP_FPS)
        cache = {}

        def frame_at(time_s):
            if time_s not in cache:
                capture.set(cv2.CAP_PROP_POS_FRAMES, round(time_s * fps))
                ok, frame = capture.read()
                if not ok:
                    raise RuntimeError(f"Frame decode failed: {row['shot_id']} {time_s}")
                cache[time_s] = cv2.resize(frame, (640, 360),
                                           interpolation=cv2.INTER_AREA)
            return cache[time_s]

        pairs = sample_track_camera_motion(points, frame_at, step_s=0.4) if points else []
        capture.release()
        residuals = [pair["camera_residual_px"] for pair in pairs
                     if pair["camera_residual_px"] is not None]
        out = {
            "source": row["source"], "shot_id": row["shot_id"],
            "candidate_colour": row["candidate_colour"],
            "top_transit": row["evidence"][row["candidate_colour"]]["transits"][:1],
            "pair_count": len(pairs),
            "reliable_pair_count": len(residuals),
            "reliable_over_10px_count": sum(value > 10 for value in residuals),
            "max_reliable_residual_px": max(residuals, default=None),
            "pairs": pairs,
        }
        output_rows.append(out)
        print(row["shot_id"], {key: out[key] for key in
              ("pair_count", "reliable_pair_count", "reliable_over_10px_count",
               "max_reliable_residual_px")}, flush=True)
    output = {
        "status": "postscore_camera_relative_object_motion_diagnostic_not_event_score",
        "source_sha256": sources,
        "input_sha256": digest(INPUT),
        "motion_code_sha256": digest(ROOT / "prototype/camera_relative_motion.py"),
        "track_link_code_sha256": digest(ROOT / "prototype/held_origin_cue.py"),
        "runner_sha256": digest(Path(__file__)),
        "pair_spacing_s": 0.4,
        "pair_duration_s": "approximately 1",
        "rows": output_rows,
        "limitations": [
            "The five cases were selected after inspecting earlier failures.",
            "Unreliable registration or a short track remains unscorable, not negative.",
            "Motion relative to the camera does not prove physical throw identity.",
        ],
    }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n")


if __name__ == "__main__":
    main()
