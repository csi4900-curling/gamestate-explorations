"""Try frozen post-cut motion only on cap-unconfirmed visual origins."""

import hashlib
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.counter_proxy_event_score import score_visual_against_counters
from prototype.postcut_colour_support import resolve_postcut_colour
from prototype.scripts.audit_pwg2022_postcut_colour import scan_receiving_view

PROXY = ROOT / "validation/official-shot-sequence/pwg2022-visual-counter-proxy.json"
REFERENCE = ROOT / "validation/official-shot-sequence/pwg2022-official-shot-ledger.json"
OUTPUT = ROOT / "validation/official-shot-sequence/pwg2022-postcut-proxy-rescue.json"
INPUTS = {
    "PREL000102": ("validation/curlobserver-learned-probe/china-full-transfer/unlabelled-shot-origin-inference.json",
                   "validation/curlobserver-learned-probe/china-full-transfer/two-shot-cap.json",
                   "validation/curlobserver-learned-probe/china-full-transfer/hard-cuts.json"),
    "PREL000103": ("validation/curlobserver-learned-probe/slovakia-full-transfer/shot-origin.json",
                   "validation/curlobserver-learned-probe/slovakia-full-transfer/two-shot-cap.json",
                   "validation/curlobserver-learned-probe/slovakia-full-transfer/hard-cuts.json"),
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first post-cut proxy rescue audit")
    proxy = json.loads(PROXY.read_text())
    reference = json.loads(REFERENCE.read_text())
    games = {game["official_game_code"]: game for game in reference["games"]}
    rows = []
    input_hashes = {}
    for proxy_row in proxy["rows"]:
        code = proxy_row["official_game_code"]
        origin_path, cap_path, cut_path = (ROOT / path for path in INPUTS[code])
        origins = json.loads(origin_path.read_text())
        cap_decisions = json.loads(cap_path.read_text())
        cuts = json.loads(cut_path.read_text())
        if cap_decisions["origins_sha256"] != digest(origin_path):
            raise ValueError("Cap decisions do not derive from these origins")
        source = games[code]
        if any(item["source_sha256"] != source["source_video_sha256"]
               for item in (origins, cap_decisions, cuts)):
            raise ValueError("Source video provenance mismatch")
        input_hashes[code] = {"origin_sha256": digest(origin_path),
                              "cap_decision_sha256": digest(cap_path),
                              "hard_cuts_sha256": digest(cut_path),
                              "source_video_sha256": source["source_video_sha256"]}
        cap_by_id = {row["shot_id"]: row for row in cap_decisions["decisions"]}
        cut_times = {round(row["time_s"], 3) for row in cuts["cuts"]}
        start, end = proxy_row["visual_search_span_s"]
        cap_video = cv2.VideoCapture(str(ROOT / source["source_video_path"]))
        if not cap_video.isOpened():
            raise RuntimeError("Video cannot be opened")
        fps = cap_video.get(cv2.CAP_PROP_FPS)
        cases = []
        rescued = list(proxy_row["visual_candidates"])
        for origin in origins["rows"]:
            if not (start <= origin["interval_s"][0] <= end and origin["predicted"]):
                continue
            decision = cap_by_id[origin["shot_id"]]
            if decision["status"] == "corroborated_candidate":
                continue
            cut_s = round(origin["interval_s"][1], 3)
            case = {"shot_id": origin["shot_id"], "origin_interval_s": origin["interval_s"],
                    "origin_probability": origin["probability"],
                    "cap_decision_status": decision["status"],
                    "verified_hard_cut": cut_s in cut_times}
            if case["verified_hard_cut"]:
                tracks, following_cuts = scan_receiving_view(cap_video, fps, cut_s)
                counts = {colour: {mode: sum(track["camera_motion_status"] !=
                                             "camera_explained_static" for track in items)
                                   for mode, items in modes.items()}
                          for colour, modes in tracks.items()}
                postcut = resolve_postcut_colour(counts)
                case.update({"postcut_counts": counts,
                             "following_cut_times_s": following_cuts,
                             "postcut_decision": postcut})
                if postcut["colour"] is not None:
                    rescued.append({"shot_id": origin["shot_id"],
                                    "interval_s": origin["interval_s"],
                                    "colour": postcut["colour"]})
            else:
                case["postcut_decision"] = {"colour": None, "status": "no_verified_cut"}
            cases.append(case)
        cap_video.release()
        after = score_visual_against_counters(rescued, proxy_row["clean_counters"])
        rows.append({"official_game_code": code, "end": proxy_row["end"],
                     "base_visual_candidate_count": len(proxy_row["visual_candidates"]),
                     "origin_cases": cases,
                     "rescued_visual_candidates": rescued,
                     "base_score": proxy_row["score"],
                     "postcut_score": after})
    output = {
        "status": "development_postcut_visual_rescue_against_counter_proxy_not_throw_f1",
        "proxy_sha256": digest(PROXY),
        "official_reference_sha256": digest(REFERENCE),
        "input_hashes_by_game": input_hashes,
        "scanner_sha256": digest(ROOT / "prototype/scripts/audit_pwg2022_postcut_colour.py"),
        "resolver_sha256": digest(ROOT / "prototype/postcut_colour_support.py"),
        "scorer_sha256": digest(ROOT / "prototype/counter_proxy_event_score.py"),
        "runner_sha256": digest(Path(__file__)),
        "rule": "For every origin-predicted but cap-unconfirmed shot in either complete-end visual search span, require a verified hard cut at the origin interval end; scan the next 12 seconds with the existing camera-filtered strict/relaxed cap-motion rule and add only a uniquely resolved colour. The counter is read only for scoring afterward.",
        "case_count": sum(len(row["origin_cases"]) for row in rows),
        "rescued_count": sum(len(row["rescued_visual_candidates"]) - row["base_visual_candidate_count"] for row in rows),
        "base_total_matched": sum(row["base_score"]["matched_count"] for row in rows),
        "postcut_total_matched": sum(row["postcut_score"]["matched_count"] for row in rows),
        "rows": rows,
        "limitations": [
            "The rescue rule was already developed on exposed 2022 video and this is an in-sample diagnostic, not a frozen unseen transfer.",
            "Post-cut motion and origin evidence need not follow the same physical stone across the edit.",
            "Official shot timestamps remain unknown; the clean broadcast counter is only a delayed weak proxy.",
            "Incomplete ends and counter-unreadable deliveries are excluded.",
        ],
    }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n")
    print({key: output[key] for key in
           ("case_count", "rescued_count", "base_total_matched", "postcut_total_matched")})


if __name__ == "__main__":
    main()
