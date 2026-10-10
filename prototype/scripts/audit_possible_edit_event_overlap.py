"""Postscan overlap of China possible edits with existing event and cap tracks."""

from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/curlobserver-learned-probe/china-full-transfer"
EDIT = BASE / "possible-edits-v1.json"
MOTION = BASE / "sequential-shot-cap-motion.json"
EVENT = BASE / "fused-shot-candidates-replay-cap.json"
OUTPUT = BASE / "possible-edit-event-overlap-postscan.json"


def digest(path):
    h = sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first postscan overlap")
    edit = json.loads(EDIT.read_text())
    motion = json.loads(MOTION.read_text())
    event = json.loads(EVENT.read_text())
    if len({edit["source_sha256"], motion["source_sha256"],
            event["source_sha256"]}) != 1:
        raise ValueError("Source fingerprint mismatch")
    by_shot = {row["shot_id"]: row for row in motion["shots"]}
    event_ids = {row["shot_id"] for row in event["events"]}
    rows = []
    for possible in edit["possible_edits_outside_hard_cuts"]:
        shot = by_shot[possible["shot_id"]]
        time_s = possible["time_s"]
        crossing = [track for track in shot["same_shot_candidates"]
                    if track["interval_s"][0] < time_s < track["interval_s"][1]]
        rows.append({
            "time_s": time_s,
            "shot_id": possible["shot_id"],
            "camera_shot_interval_s": shot["interval_s"],
            "has_fused_event_candidate": possible["shot_id"] in event_ids,
            "crossing_same_shot_cap_track_count": len(crossing),
            "crossing_same_shot_cap_track_ids": [track["id"] for track in crossing],
        })
    affected_event_ids = sorted({row["shot_id"] for row in rows
                                 if row["has_fused_event_candidate"]})
    crossing_ids = sorted({row["shot_id"] for row in rows
                           if row["crossing_same_shot_cap_track_count"]})
    output = {
        "status": "postscan_possible_edit_event_track_overlap_not_verified_edit_recall",
        "source_sha256": edit["source_sha256"],
        "sha256": {"possible_edits": digest(EDIT),
                   "cap_motion": digest(MOTION),
                   "fused_events": digest(EVENT),
                   "runner": digest(__file__)},
        "possible_edit_count": len(rows),
        "affected_event_candidate_shot_count": len(affected_event_ids),
        "affected_event_candidate_shot_ids": affected_event_ids,
        "possible_edit_crossing_cap_track_count": sum(
            bool(row["crossing_same_shot_cap_track_count"]) for row in rows),
        "shot_count_with_crossing_cap_track": len(crossing_ids),
        "shot_ids_with_crossing_cap_track": crossing_ids,
        "rows": rows,
        "limitations": [
            "Possible edits are unverified threshold proposals, not certified camera cuts.",
            "A cap track crossing a possible edit may still be valid; this audit only flags identity risk.",
            "Fused events are provisional and have no independent physical throw F1.",
        ],
    }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n")
    print({"possible": len(rows), "event_shots": len(affected_event_ids),
           "crossing_edit_rows": output["possible_edit_crossing_cap_track_count"],
           "crossing_shots": len(crossing_ids)})


if __name__ == "__main__":
    main()
