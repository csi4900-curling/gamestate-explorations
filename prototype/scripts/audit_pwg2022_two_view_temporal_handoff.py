"""Time the receiving-view tracks for source-colour-concordant 2022 cues."""

from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from scripts.audit_pwg2022_postcut_colour import scan_receiving_view

BASE = ROOT / "validation/official-shot-sequence"
COLOUR = BASE / "pwg2022-cross-view-source-colour-handoff-development.json"
POSTCUT = BASE / "pwg2022-visual-only-postcut-colours.json"
PASSAGES = {
    "PREL000101": BASE / "swiss-provisional-release-transfer-first.json",
    "PREL000102": BASE / "china-provisional-release-transfer-first.json",
    "PREL000103": BASE / "slovakia-provisional-release-coverage-development.json",
}
VIDEOS = {
    "PREL000101": ROOT
    / "validation/throw-event-benchmark/paralympics-2022-sweden-switzerland/source.mp4",
    "PREL000102": ROOT
    / "validation/throw-event-benchmark/paralympics-2022-canada-china/source.mp4",
    "PREL000103": ROOT
    / "validation/throw-event-benchmark/paralympics-2022-slovakia-usa/source.mp4",
}
OUTPUT = BASE / "pwg2022-two-view-temporal-handoff-development.json"


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def build():
    colour = json.loads(COLOUR.read_text())
    postcut = json.loads(POSTCUT.read_text())
    post_by_game = {game["official_game_code_for_join_only"]: game for game in postcut["games"]}
    if len(post_by_game) != len(postcut["games"]):
        raise ValueError("Duplicate postcut game")
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    games = []
    for game in colour["games"]:
        code = game["recording_code"]
        candidates = [row for row in game["rows"] if row["source_colour"] is not None]
        passage = json.loads(PASSAGES[code].read_text())
        passage_by_id = {row["event_id"]: row for row in passage["rows"]}
        sidecar = post_by_game[code]
        post_by_shot = {row["shot_id"]: row for row in sidecar["rows"]}
        source_hash = digest(VIDEOS[code])
        if (
            source_hash != game["source_sha256"]
            or source_hash != passage["source_sha256"]
            or source_hash != sidecar["source_video_sha256"]
            or source_hash == reserved["source_sha256"]
        ):
            raise ValueError(f"Source mismatch or reserved game: {code}")
        capture = cv2.VideoCapture(str(VIDEOS[code]), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
        if not capture.isOpened():
            raise RuntimeError(f"Cannot open source: {code}")
        fps = capture.get(cv2.CAP_PROP_FPS)
        rows = []
        for candidate in candidates:
            original = passage_by_id[candidate["event_id"]]
            prior_post = post_by_shot[candidate["origin_shot_id"]]
            cut_s = original["delivery_window_s"][1]
            tracks, further_cuts = scan_receiving_view(capture, fps, cut_s)
            qualifying = [
                track
                for track in tracks[candidate["source_colour"]]["strict"]
                if track["camera_motion_status"] != "camera_explained_static"
            ]
            frozen_count = prior_post["postcut_track_counts_after_camera_filter"][
                candidate["source_colour"]
            ]["strict"]
            if len(qualifying) != frozen_count:
                raise ValueError(f"Frozen postcut scan changed: {code} {candidate['event_id']}")
            starts = [track["time_interval_s"][0] for track in qualifying]
            first_start = min(starts) if starts else None
            rows.append(
                {
                    **candidate,
                    "cut_time_s": cut_s,
                    "receiving_window_s": [round(cut_s + 0.2, 3), round(cut_s + 12, 3)],
                    "further_cut_times_s": further_cuts,
                    "qualifying_strict_track_count": len(qualifying),
                    "qualifying_track_intervals_s": [row["time_interval_s"] for row in qualifying],
                    "qualifying_track_camera_motion_status": [
                        row["camera_motion_status"] for row in qualifying
                    ],
                    "first_receiving_motion_s": first_start,
                    "cue_to_receiving_motion_s": (
                        round(first_start - candidate["release_cue_s"], 3)
                        if first_start is not None
                        else None
                    ),
                    "cut_to_receiving_motion_s": (
                        round(first_start - cut_s, 3) if first_start is not None else None
                    ),
                    "physical_stone_identity_verified": False,
                }
            )
            print(f"{code} {candidate['event_id']} {len(qualifying)} tracks", flush=True)
        capture.release()
        games.append(
            {
                "recording_code": code,
                "source_sha256": source_hash,
                "source_colour_concordance_count": len(rows),
                "unique_receiving_track_count": sum(
                    row["qualifying_strict_track_count"] == 1 for row in rows
                ),
                "rows": rows,
            }
        )
    return {
        "status": "development_two_view_temporal_handoff_not_physical_identity",
        "source_colour_handoff_sha256": digest(COLOUR),
        "postcut_sha256": digest(POSTCUT),
        "postcut_scanner_sha256": digest(
            ROOT / "prototype/scripts/audit_pwg2022_postcut_colour.py"
        ),
        "runner_sha256": digest(Path(__file__)),
        "passage_input_sha256": {code: digest(path) for code, path in PASSAGES.items()},
        "games": games,
        "limitations": [
            "The 16 cases were selected after seeing within-view and post-cut colour agreement on exposed recordings.",
            "A qualifying same-colour receiving track can be a different physical stone, equipment, or camera-relative association error.",
            "The timing gap is evidence compatibility, not a continuous trajectory, exact release, or verified settle position.",
            "No event or counter association, physical event F1, or simulation-ready state changes.",
        ],
    }


def main():
    payload = json.dumps(build(), indent=2) + "\n"
    if OUTPUT.exists():
        if OUTPUT.read_text() != payload:
            raise SystemExit("Existing temporal handoff differs from inputs or code")
        print(f"Verified {OUTPUT}")
    else:
        OUTPUT.write_text(payload)
        print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
