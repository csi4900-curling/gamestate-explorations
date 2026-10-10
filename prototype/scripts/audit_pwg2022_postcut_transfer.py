"""Stress-test frozen post-cut colour rule on counter-anchored 2022 shots."""

from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

import cv2


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from scene_cuts import scene_cut_evidence
from postcut_colour_support import resolve_postcut_colour
from scripts.audit_pwg2022_postcut_colour import scan_receiving_view

REFERENCE = ROOT / "validation/official-shot-sequence/pwg2022-official-shot-ledger.json"
ALIGNMENT = ROOT / "validation/official-shot-sequence/pwg2022-official-counter-alignment.json"
OUTPUT = ROOT / "validation/official-shot-sequence/pwg2022-postcut-colour-transfer.json"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def spread_sample(rows, count=24):
    if len(rows) <= count:
        return rows
    return [rows[round(index * (len(rows) - 1) / (count - 1))]
            for index in range(count)]


def verified_cut(cap, fps, time_s):
    frames = []
    for offset in (-0.2, 0.2):
        cap.set(cv2.CAP_PROP_POS_FRAMES, round((time_s + offset) * fps))
        ok, frame = cap.read()
        if not ok:
            return False
        frames.append(frame)
    return scene_cut_evidence(*frames)["hard_cut"]


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first transfer audit")
    reference = json.loads(REFERENCE.read_text())
    alignment = json.loads(ALIGNMENT.read_text())
    if alignment["official_reference_sha256"] != digest(REFERENCE):
        raise ValueError("Alignment uses different official reference")
    aligned = {game["official_game_code"]: game for game in alignment["games"]}
    rows = []
    for game in reference["games"]:
        code = game["official_game_code"]
        info = aligned[code]
        candidate_path = ROOT / info["candidate_ledger_path"]
        if digest(candidate_path) != info["candidate_ledger_sha256"]:
            raise ValueError("Candidate ledger differs from alignment")
        candidates = {event["candidate_id"]: event
                      for event in json.loads(candidate_path.read_text())["events"]}
        links = [link for link in info["candidate_links"]
                 if link["official_shot_id"] and
                 candidates[link["candidate_id"]]["evidence_class"] == "origin_view_candidate"
                 and link["counter_alignment_status"] in
                 ("unique_colour_concordant", "unique_colour_concordant_amid_duplicate",
                  "candidate_colour_unknown")]
        links = spread_sample(links)
        video = ROOT / game["source_video_path"]
        if digest(video) != game["source_video_sha256"]:
            raise ValueError("Source video hash differs from official reference")
        cap = cv2.VideoCapture(str(video))
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open {video}")
        fps = cap.get(cv2.CAP_PROP_FPS)
        for link in links:
            candidate = candidates[link["candidate_id"]]
            cut_s = candidate["release_window_s"][1]
            cut_is_verified = verified_cut(cap, fps, cut_s)
            result = {
                "official_game_code": code,
                "official_shot_id": link["official_shot_id"],
                "official_colour": link["official_colour"],
                "candidate_id": link["candidate_id"],
                "candidate_colour": candidate["colour"],
                "cut_time_s": cut_s,
                "cut_verified": cut_is_verified,
            }
            if cut_is_verified:
                tracks, further_cuts = scan_receiving_view(cap, fps, cut_s)
                counts = {colour: {mode: sum(item["camera_motion_status"] !=
                                              "camera_explained_static" for item in items)
                                   for mode, items in modes.items()}
                          for colour, modes in tracks.items()}
                decision = resolve_postcut_colour(counts)
                result.update({
                    "track_counts_after_camera_filter": counts,
                    "further_cut_times_s": further_cuts,
                    "decision": decision,
                    "decision_matches_official_colour": (decision["colour"] == link["official_colour"]
                                                         if decision["colour"] else None),
                })
            else:
                result.update({"decision": {"colour": None, "status": "unverified_cut"},
                               "decision_matches_official_colour": None})
            rows.append(result)
        cap.release()
    output = {
        "status": "counter_anchored_postcut_colour_transfer_diagnostic_not_event_f1",
        "official_reference_sha256": digest(REFERENCE),
        "alignment_sha256": digest(ALIGNMENT),
        "resolver_code_sha256": digest(ROOT / "prototype/postcut_colour_support.py"),
        "scanner_code_sha256": digest(ROOT / "prototype/scripts/audit_pwg2022_postcut_colour.py"),
        "runner_sha256": digest(Path(__file__)),
        "sample_rule": "Up to 24 evenly spaced eligible origin-view candidate links per game, ordered by video time; no selection by official colour.",
        "sample_count": len(rows),
        "decision_status_counts": dict(Counter(row["decision"]["status"] for row in rows)),
        "resolved_correct_colour_count": sum(row["decision_matches_official_colour"] is True
                                             for row in rows),
        "resolved_wrong_colour_count": sum(row["decision_matches_official_colour"] is False
                                           for row in rows),
        "rows": rows,
        "limitations": [
            "These are development candidates from the same three recordings; this is a transfer stress check, not a held-out benchmark.",
            "The official colour checks handle identity only; it does not verify physical throw time or candidate event precision.",
            "The counter link and cut requirements select easier observed shots and leave other shots outside the sample.",
        ],
    }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n")
    print(output["sample_count"], output["decision_status_counts"],
          output["resolved_correct_colour_count"], output["resolved_wrong_colour_count"])


if __name__ == "__main__":
    main()
