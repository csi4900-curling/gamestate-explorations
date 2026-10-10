"""Apply the frozen post-cut motion scanner to two source-only rescue proposals."""

from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from postcut_colour_support import resolve_postcut_colour
from scripts.audit_pwg2022_postcut_colour import scan_receiving_view
from scripts.audit_pwg2022_postcut_transfer import verified_cut

BASE = ROOT / "validation/official-shot-sequence"
PROPOSALS = BASE / "pwg2022-outside-union-release-rescue-proposals-development.json"
OUTPUT = BASE / "pwg2022-outside-union-receiving-view-development.json"
VIDEOS = {
    "PREL000101": ROOT
    / "validation/throw-event-benchmark/paralympics-2022-sweden-switzerland/source.mp4",
    "PREL000102": ROOT
    / "validation/throw-event-benchmark/paralympics-2022-canada-china/source.mp4",
}


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def build():
    proposals = json.loads(PROPOSALS.read_text())["proposals"]
    if len(proposals) != 2:
        raise ValueError("Unexpected rescue proposal count")
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    rows = []
    for proposal in proposals:
        video = VIDEOS[proposal["recording_code"]]
        if digest(video) != proposal["source_sha256"] or digest(video) == reserved["source_sha256"]:
            raise ValueError("Source mismatch or reserved-source overlap")
        capture = cv2.VideoCapture(str(video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
        if not capture.isOpened():
            raise RuntimeError("Cannot open source video")
        try:
            fps = capture.get(cv2.CAP_PROP_FPS)
            cut_s = proposal["origin_shot_interval_s"][1]
            hard_cut = verified_cut(capture, fps, cut_s)
            if hard_cut:
                tracks, further_cuts = scan_receiving_view(capture, fps, cut_s)
                counts = {
                    colour: {
                        mode: sum(
                            track["camera_motion_status"] != "camera_explained_static"
                            for track in mode_rows
                        )
                        for mode, mode_rows in modes.items()
                    }
                    for colour, modes in tracks.items()
                }
                decision = resolve_postcut_colour(counts)
            else:
                tracks, further_cuts, counts = None, [], None
                decision = {"colour": None, "status": "unverified_cut"}
            rows.append(
                {
                    "proposal_id": proposal["proposal_id"],
                    "recording_code": proposal["recording_code"],
                    "origin_shot_id": proposal["origin_shot_id"],
                    "release_cue_s": proposal["release_cue_s"],
                    "origin_colour": proposal["observed_colour"],
                    "cut_time_s": cut_s,
                    "hard_cut_verified": hard_cut,
                    "receiving_window_s": [round(cut_s + 0.2, 3), round(cut_s + 12, 3)],
                    "further_cut_times_s": further_cuts,
                    "track_counts_after_camera_filter": counts,
                    "tracks": tracks,
                    "decision": decision,
                    "source_colour_agreement": (
                        decision["colour"] == proposal["observed_colour"]
                        if decision["colour"]
                        else None
                    ),
                    "physical_stone_identity_verified": False,
                }
            )
        finally:
            capture.release()
    return {
        "status": "development_outside_union_two_view_colour_not_physical_identity",
        "input_sha256": {
            "proposals": digest(PROPOSALS),
            "postcut_scanner": digest(ROOT / "prototype/scripts/audit_pwg2022_postcut_colour.py"),
            "cut_check": digest(ROOT / "prototype/scripts/audit_pwg2022_postcut_transfer.py"),
            "resolver": digest(ROOT / "prototype/postcut_colour_support.py"),
            "runner": digest(Path(__file__)),
        },
        "proposal_count": len(rows),
        "rows": rows,
        "limitations": [
            "Receiving-view colour and motion are independent source-video cues, not a persistent physical stone ID.",
            "Camera-motion registration may be unresolved; apparent movement can include camera motion or another stone.",
            "The two windows are selected postscan recall leads, not independent event labels or a full-video F1 score.",
        ],
    }


def main():
    payload = json.dumps(build(), indent=2) + "\n"
    if OUTPUT.exists() and OUTPUT.read_text() != payload:
        raise SystemExit("Existing receiving audit differs from hashed source evidence")
    if not OUTPUT.exists():
        OUTPUT.write_text(payload)
    print(f"Verified {OUTPUT}")


if __name__ == "__main__":
    main()
