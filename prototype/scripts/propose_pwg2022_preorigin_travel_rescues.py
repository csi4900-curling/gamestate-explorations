"""Find unassigned receiving travel directly after an unassigned origin-like shot."""

from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from scripts.audit_pwg2022_postcut_transfer import verified_cut

BASE = ROOT / "validation/official-shot-sequence"
SUMMARY = BASE / "pwg2022-all-unassigned-shots-source-scan-summary-development.json"
UNION = BASE / "pwg2022-provisional-event-evidence-union-v2-source-rescues-development.json"
SOURCES = {
    "PREL000101": {
        "origins": ROOT
        / "validation/curlobserver-learned-probe/swiss-full-transfer/shot-origin.json",
        "motion": ROOT
        / "validation/curlobserver-learned-probe/swiss-full-transfer/cap-motion.json",
        "counter": ROOT
        / "validation/curlobserver-learned-probe/swiss-full-transfer/counter-replay.json",
        "video": ROOT
        / "validation/throw-event-benchmark/paralympics-2022-sweden-switzerland/source.mp4",
    },
    "PREL000102": {
        "origins": ROOT
        / "validation/curlobserver-learned-probe/china-full-transfer/unlabelled-shot-origin-inference.json",
        "motion": ROOT
        / "validation/curlobserver-learned-probe/china-full-transfer/sequential-shot-cap-motion.json",
        "counter": ROOT
        / "validation/throw-event-benchmark/layout-router/full-china22-counter-postscore-replay.json",
        "video": ROOT / "validation/throw-event-benchmark/paralympics-2022-canada-china/source.mp4",
    },
    "PREL000103": {
        "origins": ROOT
        / "validation/curlobserver-learned-probe/slovakia-full-transfer/shot-origin.json",
        "motion": ROOT
        / "validation/curlobserver-learned-probe/slovakia-full-transfer/cap-motion.json",
        "counter": ROOT
        / "validation/curlobserver-learned-probe/slovakia-full-transfer/counter-replay.json",
        "video": ROOT / "validation/throw-event-benchmark/paralympics-2022-slovakia-usa/source.mp4",
    },
}
OUTPUT = BASE / "pwg2022-preorigin-travel-rescue-proposals-development.json"


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def build():
    summary = json.loads(SUMMARY.read_text())
    union = json.loads(UNION.read_text())
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    unions = {game["official_game_code"]: game for game in union["games"]}
    triage = []
    proposals = []
    input_hashes = {}
    for game in summary["games"]:
        code = game["recording_code"]
        paths = SOURCES[code]
        input_hashes[code] = {name: digest(path) for name, path in paths.items()}
        origins = json.loads(paths["origins"].read_text())
        motion = json.loads(paths["motion"].read_text())
        counters = json.loads(paths["counter"].read_text())
        source = unions[code]["source_sha256"]
        if (
            source == reserved["source_sha256"]
            or any(row["source_sha256"] != source for row in (origins, motion, counters))
            or input_hashes[code]["video"] != source
        ):
            raise ValueError("Input source mismatch or reserved-source overlap")
        shots = origins["rows"]
        shot_index = {row["shot_id"]: index for index, row in enumerate(shots)}
        motion_by_shot = {row["shot_id"]: row for row in motion["shots"]}
        assigned_shots = {
            sid for event in unions[code]["events"] for sid in event["source_shot_ids"]
        }
        assigned_counters = {
            event["counter_id"]
            for event in unions[code]["events"]
            if event["counter_id"] is not None
        }
        capture = cv2.VideoCapture(str(paths["video"]), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
        if not capture.isOpened():
            raise RuntimeError("Cannot open source video")
        try:
            fps = capture.get(cv2.CAP_PROP_FPS)
            for candidate in game["candidates"]:
                shot_id = candidate["shot_id"]
                index = shot_index[shot_id]
                previous = shots[index - 1] if index else None
                row = {
                    "recording_code": code,
                    "receiving_shot_id": shot_id,
                    "receiving_shot_interval_s": candidate["interval_s"],
                    "raw_cue_interpreted_as_release": False,
                    "previous_shot_id": previous["shot_id"] if previous else None,
                    "previous_shot_origin_predicted": bool(previous["predicted"])
                    if previous
                    else False,
                }
                if (
                    not previous
                    or not previous["predicted"]
                    or previous["shot_id"] in assigned_shots
                ):
                    row["status"] = "no_unassigned_predicted_origin_predecessor"
                    triage.append(row)
                    continue
                cut_s = candidate["interval_s"][0]
                if previous["interval_s"][1] != cut_s or not verified_cut(capture, fps, cut_s):
                    row["status"] = "no_verified_adjacent_cut"
                    triage.append(row)
                    continue
                colour = candidate["passages"][0]["colour"]
                tracks = [
                    track
                    for track in motion_by_shot[shot_id]["same_shot_candidates"]
                    if track["colour"] == colour
                    and track["interval_s"][0] <= cut_s + 0.4
                    and track["span_px"] >= 100
                    and track["point_count"] >= 10
                ]
                if len(tracks) != 1:
                    row["status"] = "no_unique_receiving_cap_track"
                    triage.append(row)
                    continue
                counter_matches = [
                    counter
                    for counter in counters["counter_events"]
                    if counter["colour"] == colour
                    and counter["id"] not in assigned_counters
                    and cut_s <= counter["crossing_time_s"] <= candidate["interval_s"][1] + 5
                ]
                if len(counter_matches) != 1:
                    row["status"] = "no_unique_unassigned_delayed_counter"
                    triage.append(row)
                    continue
                track, counter = tracks[0], counter_matches[0]
                row["status"] = "source_counter_travel_rescue_proposal"
                row["counter_id"] = counter["id"]
                triage.append(row)
                proposals.append(
                    {
                        "proposal_id": f"TRAVEL-{counter['id']}",
                        "recording_code": code,
                        "source_sha256": source,
                        "origin_shot_id": previous["shot_id"],
                        "origin_shot_interval_s": previous["interval_s"],
                        "origin_probability": previous["probability"],
                        "receiving_shot_id": shot_id,
                        "receiving_shot_interval_s": candidate["interval_s"],
                        "receiving_track": track,
                        "counter_id": counter["id"],
                        "counter_colour": counter["colour"],
                        "counter_time_s": counter["crossing_time_s"],
                        "counter_evidence_interval_s": counter["evidence_interval_s"],
                        "visible_release_cue_s": None,
                        "physical_stone_identity_verified": False,
                        "simulation_ready": False,
                    }
                )
        finally:
            capture.release()
    return {
        "status": "development_preorigin_receiving_travel_rescue_not_physical_f1",
        "selection_rule": "Among frozen model-negative ice-supported unassigned shots, require an unassigned origin-predicted immediately preceding shot, verified cut, one same-colour substantial receiving cap track, and one same-colour unassigned delayed counter update within five seconds of the receiving shot end.",
        "input_sha256": {
            "full_scan_summary": digest(SUMMARY),
            "union_v2": digest(UNION),
            "sources": input_hashes,
            "cut_check_code": digest(ROOT / "prototype/scripts/audit_pwg2022_postcut_transfer.py"),
            "runner": digest(Path(__file__)),
        },
        "triaged_candidate_count": len(triage),
        "proposal_count": len(proposals),
        "triage": triage,
        "proposals": proposals,
        "limitations": [
            "The rule was developed after viewing exposed source cases; this is not a frozen transfer or independent event F1.",
            "The ice-supported cue in a receiving view is classified as travel evidence, never as a release instant.",
            "Origin view and receiving track colour, delayed counter and timing do not establish persistent physical stone identity.",
        ],
    }


def main():
    payload = json.dumps(build(), indent=2) + "\n"
    if OUTPUT.exists() and OUTPUT.read_text() != payload:
        raise SystemExit("Existing travel rescue differs from hashed inputs")
    if not OUTPUT.exists():
        OUTPUT.write_text(payload)
    print(f"Verified {OUTPUT}")


if __name__ == "__main__":
    main()
