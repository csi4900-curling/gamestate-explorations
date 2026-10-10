"""Compare selected Norway and Swiss fallback track shapes without rescoring events."""

from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
sys.path.insert(0, str(ROOT / "prototype/scripts"))
from audit_china_nonorigin_track_continuity import step_shape
from audit_nonorigin_camera_relative import selected_track

BASE = ROOT / "validation/curlobserver-learned-probe/cap-patch-crossmatch-v1"
INPUT = BASE / "nonorigin-cap-object-audit-development.json"
CAMERA = BASE / "nonorigin-camera-relative-audit-development.json"
OUTPUT = BASE / "nonorigin-track-continuity-development.json"
VIDEOS = {
    "norway": ROOT / "validation/throw-event-benchmark/paralympics-2022-canada-norway/source.mp4",
    "swiss": ROOT / "validation/throw-event-benchmark/paralympics-2022-sweden-switzerland/source.mp4",
}


def digest(path):
    h = sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first cross-recording track audit")
    data = json.loads(INPUT.read_text())
    camera = json.loads(CAMERA.read_text())
    source_hashes = {name: digest(path) for name, path in VIDEOS.items()}
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    if (source_hashes != data["source_sha256"] or
            reserved["source_sha256"] in source_hashes.values()):
        raise ValueError("Source hashes changed or reserved source selected")
    camera_rows = {(row["source"], row["shot_id"]): row
                   for row in camera["rows"]}
    rows = []
    for row in data["rows"]:
        key = (row["source"], row["shot_id"])
        track = selected_track(row)
        motion = camera_rows[key]
        rows.append({
            "source": row["source"],
            "shot_id": row["shot_id"],
            "candidate_colour": row["candidate_colour"],
            "top_transit": row["evidence"][row["candidate_colour"]]["transits"][:1],
            "step_shape": step_shape(track) if track else None,
            "reliable_camera_pair_count": motion["reliable_pair_count"],
            "reliable_camera_pairs_over_10px": motion["reliable_over_10px_count"],
            "max_reliable_camera_residual_px": motion["max_reliable_residual_px"],
        })
    output = {
        "status": "selected_postscore_cross_recording_track_shape_diagnostic_not_event_score",
        "source_sha256": source_hashes,
        "input_sha256": digest(INPUT),
        "camera_audit_sha256": digest(CAMERA),
        "track_shape_code_sha256": digest(ROOT / "prototype/scripts/audit_china_nonorigin_track_continuity.py"),
        "link_code_sha256": digest(ROOT / "prototype/scripts/audit_nonorigin_camera_relative.py"),
        "runner_sha256": digest(__file__),
        "rows": rows,
        "limitations": [
            "These five cases were selected after earlier fallback inspection.",
            "Distributed raw image motion can be caused by camera panning.",
            "Camera-relative registration can abstain or still follow the wrong cap-like patch.",
            "No independent physical throw labels or event F1 are supplied.",
        ],
    }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n")
    print([(row["shot_id"], row["step_shape"]["largest_step_fraction"]
            if row["step_shape"] else None,
            row["step_shape"]["steps_over_5px"] if row["step_shape"] else None,
            row["reliable_camera_pairs_over_10px"])
           for row in rows])


if __name__ == "__main__":
    main()
