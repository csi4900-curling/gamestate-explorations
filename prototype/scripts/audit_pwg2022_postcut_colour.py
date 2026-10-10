"""Check whether the receiving view resolves gap-candidate handle colour."""

from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

import cv2


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from camera_relative_motion import sample_track_camera_motion
from postcut_colour_support import camera_motion_status, resolve_postcut_colour
from scene_cuts import scene_cut_evidence
from stone_motion_fallback import moving_cap_tracks, stone_cap_candidates

REFERENCE = ROOT / "validation/official-shot-sequence/pwg2022-official-shot-ledger.json"
PROBE = ROOT / "validation/official-shot-sequence/pwg2022-bounded-gap-motion-probe.json"
OUTPUT = ROOT / "validation/official-shot-sequence/pwg2022-postcut-colour-audit.json"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def scan_receiving_view(cap, fps, cut_s):
    observations = {colour: {"strict": [], "relaxed": []}
                    for colour in ("red", "yellow")}
    cuts = []
    previous = None
    for tick in range(round(cut_s * 5) + 1, round((cut_s + 12) * 5) + 1):
        time_s = round(tick / 5, 3)
        cap.set(cv2.CAP_PROP_POS_FRAMES, round(time_s * fps))
        ok, frame = cap.read()
        if not ok:
            raise RuntimeError(f"Frame decode failed at {time_s}")
        if previous is not None and scene_cut_evidence(previous, frame)["hard_cut"]:
            cuts.append(time_s)
        for colour in observations:
            observations[colour]["strict"].append(
                (time_s, stone_cap_candidates(frame, colour)))
            observations[colour]["relaxed"].append(
                (time_s, stone_cap_candidates(frame, colour,
                                              allow_bright_body=True,
                                              allow_large_caps=True)))
        previous = frame
    tracks = {}
    def frame_at(time_s):
        cap.set(cv2.CAP_PROP_POS_FRAMES, round(time_s * fps))
        ok, frame = cap.read()
        if not ok:
            raise RuntimeError(f"Frame decode failed at {time_s}")
        return cv2.resize(frame, (640, 360), interpolation=cv2.INTER_AREA)

    for colour, modes in observations.items():
        tracks[colour] = {}
        for mode, samples in modes.items():
            found = moving_cap_tracks(samples, max_gap_s=0.5, cut_times_s=cuts)
            tracks[colour][mode] = []
            for row in found:
                camera_rows = sample_track_camera_motion(row["points"], frame_at)
                tracks[colour][mode].append({
                    "time_interval_s": [row["points"][0]["time_s"],
                                        row["points"][-1]["time_s"]],
                    "span_px": round(row["span_px"], 2),
                    "observations": len(row["points"]),
                    "camera_motion_pairs": camera_rows,
                    "camera_motion_status": camera_motion_status(camera_rows),
                })
    return tracks, cuts


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first postcut colour audit")
    reference = json.loads(REFERENCE.read_text())
    probe = json.loads(PROBE.read_text())
    if probe["official_reference_sha256"] != digest(REFERENCE):
        raise ValueError("Probe uses a different official reference")
    sources = {game["official_game_code"]: game for game in reference["games"]}
    results = []
    for code, game in sources.items():
        selected = [row for row in probe["results"] if row["official_game_code"] == code]
        video = ROOT / game["source_video_path"]
        if digest(video) != game["source_video_sha256"]:
            raise ValueError("Video differs from official reference")
        cap = cv2.VideoCapture(str(video))
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open {video}")
        fps = cap.get(cv2.CAP_PROP_FPS)
        for row in selected:
            cut_s = row["candidate_release_window_s"][1]
            if not any(abs(cut_s - cut) < 0.01 for cut in row["hard_cut_times_s"]):
                raise ValueError(f"Candidate {row['candidate_id']} is not followed by a verified cut")
            tracks, further_cuts = scan_receiving_view(cap, fps, cut_s)
            raw_counts = {colour: {mode: len(items) for mode, items in modes.items()}
                          for colour, modes in tracks.items()}
            counts = {colour: {mode: sum(item["camera_motion_status"] !=
                                          "camera_explained_static" for item in items)
                               for mode, items in modes.items()}
                      for colour, modes in tracks.items()}
            decision = resolve_postcut_colour(counts)
            results.append({
                "official_game_code": code,
                "official_shot_id": row["official_shot_id"],
                "official_colour": row["expected_colour"],
                "candidate_id": row["candidate_id"],
                "candidate_colour": row["candidate_colour"],
                "cut_time_s": cut_s,
                "receiving_view_window_s": [round(cut_s + 0.2, 3), round(cut_s + 12, 3)],
                "further_cut_times_s": further_cuts,
                "raw_track_counts": raw_counts,
                "track_counts_after_camera_filter": counts,
                "tracks": tracks,
                "decision": decision,
                "decision_matches_official_colour": (decision["colour"] == row["expected_colour"]
                                                     if decision["colour"] else None),
            })
        cap.release()
    output = {
        "status": "postcut_colour_development_diagnostic_not_throw_identity_or_f1",
        "official_reference_sha256": digest(REFERENCE),
        "source_probe_sha256": digest(PROBE),
        "resolver_code_sha256": digest(ROOT / "prototype/postcut_colour_support.py"),
        "runner_sha256": digest(Path(__file__)),
        "camera_motion_code_sha256": digest(ROOT / "prototype/camera_relative_motion.py"),
        "selected_gap_count": len(results),
        "decision_status_counts": dict(Counter(row["decision"]["status"] for row in results)),
        "resolved_colour_count": sum(row["decision"]["colour"] is not None for row in results),
        "resolved_correct_colour_count": sum(row["decision_matches_official_colour"] is True
                                             for row in results),
        "resolved_wrong_colour_count": sum(row["decision_matches_official_colour"] is False
                                           for row in results),
        "results": results,
        "limitations": [
            "Candidate windows and shot links were selected during development; this is not held-out colour accuracy or event F1.",
            "Motion immediately after a cut does not prove it is the stone seen before the cut.",
            "The official colour is used only for evaluation, never for the visual decision.",
            "A missing or ambiguous track causes abstention; the proposed release window can still be wrong.",
        ],
    }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n")
    print(output["selected_gap_count"], output["decision_status_counts"],
          output["resolved_correct_colour_count"], output["resolved_wrong_colour_count"])


if __name__ == "__main__":
    main()
