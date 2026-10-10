"""Test source-visible ice as a conservative counter-shot tie-break."""

from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from scripts.audit_candidate_ice_coverage import ice_fractions

BASE = ROOT / "validation/curlobserver-learned-probe"
REFERENCE = ROOT / "validation/official-shot-sequence/pwg2022-official-shot-ledger.json"
INPUTS = {
    "PREL000101": (BASE / "swiss-full-transfer/counter-cap.json",
                   BASE / "swiss-full-transfer/shot-origin.json"),
    "PREL000102": (BASE / "china-full-transfer/counter-shot-alignment-replay-cap.json",
                   BASE / "china-full-transfer/unlabelled-shot-origin-inference.json"),
    "PREL000103": (BASE / "slovakia-full-transfer/counter-cap.json",
                   BASE / "slovakia-full-transfer/shot-origin.json"),
}
OUTPUT = ROOT / "validation/official-shot-sequence/pwg2022-ambiguous-counter-ice-tiebreak-development.json"
MIN_ORIGIN_PROBABILITY = 0.2
MIN_MAX_CENTER_LOWER_ICE = 0.25
SAMPLE_FRACTIONS = (0.25, 0.5, 0.75)


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def select_unique_ice_supported(options):
    selected = [row for row in options
                if row["origin_probability"] >= MIN_ORIGIN_PROBABILITY and
                row["max_center_lower_ice_fraction"] >= MIN_MAX_CENTER_LOWER_ICE]
    return selected[0]["shot_id"] if len(selected) == 1 else None


def build():
    reference = json.loads(REFERENCE.read_text())
    by_code = {row["official_game_code"]: row for row in reference["games"]}
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    games = []
    for code, (align_path, origin_path) in INPUTS.items():
        alignment, origins = (json.loads(path.read_text()) for path in
                              (align_path, origin_path))
        source = origins["source_sha256"]
        video = by_code[code]
        if (source == reserved["source_sha256"] or
                alignment["source_sha256"] != source or
                video["source_video_sha256"] != source):
            raise ValueError(f"Source mismatch or reserved source selected: {code}")
        source_video = ROOT / video["source_video_path"]
        if digest(source_video) != source:
            raise ValueError(f"Source video fingerprint differs: {code}")
        capture = cv2.VideoCapture(str(source_video))
        if not capture.isOpened():
            raise RuntimeError(f"Cannot open source: {code}")
        fps = capture.get(cv2.CAP_PROP_FPS)
        origin_by_shot = {row["shot_id"]: row for row in origins["rows"]}
        rows = []
        for counter in alignment["rows"]:
            if counter["shot_id"] is not None or len(counter["candidate_shots"]) < 2:
                continue
            options = []
            for candidate in counter["candidate_shots"]:
                shot_id = candidate["shot_id"]
                shot = origin_by_shot[shot_id]
                if shot["interval_s"] != candidate["interval_s"]:
                    raise ValueError(f"Candidate/shot interval differs: {code} {shot_id}")
                start, end = shot["interval_s"]
                samples = []
                for fraction in SAMPLE_FRACTIONS:
                    time_s = start + fraction * (end - start)
                    capture.set(cv2.CAP_PROP_POS_FRAMES, round(time_s * fps))
                    ok, frame = capture.read()
                    if not ok:
                        raise RuntimeError(f"Frame decode failed: {code} {time_s}")
                    samples.append({"time_s": round(time_s, 3),
                                    "ice_fraction": ice_fractions(frame)})
                options.append({
                    "shot_id": shot_id,
                    "interval_s": shot["interval_s"],
                    "origin_probability": candidate["origin_probability"],
                    "max_center_lower_ice_fraction": max(
                        row["ice_fraction"]["center_lower"] for row in samples),
                    "samples": samples,
                })
            chosen = select_unique_ice_supported(options)
            rows.append({
                "counter_id": counter["counter_id"],
                "counter_colour": counter["colour"],
                "counter_update_s": counter["counter_update_s"],
                "chosen_shot_id": chosen,
                "status": "unique_ice_supported_option" if chosen else "abstained",
                "options": options,
            })
        capture.release()
        games.append({
            "official_game_code": code,
            "source_sha256": source,
            "input_sha256": {"counter_alignment": digest(align_path),
                             "shot_origins": digest(origin_path),
                             "source_video": source},
            "multi_option_counter_count": len(rows),
            "unique_ice_choice_count": sum(row["chosen_shot_id"] is not None for row in rows),
            "rows": rows,
        })
    return {
        "status": "postscore_exposed_source_ice_tiebreak_diagnostic_not_event_f1",
        "reference_metadata_sha256": digest(REFERENCE),
        "ice_code_sha256": digest(ROOT / "prototype/scripts/audit_candidate_ice_coverage.py"),
        "runner_sha256": digest(Path(__file__)),
        "rule": {"minimum_origin_probability": MIN_ORIGIN_PROBABILITY,
                 "minimum_max_center_lower_ice_fraction": MIN_MAX_CENTER_LOWER_ICE,
                 "sample_fractions": list(SAMPLE_FRACTIONS),
                 "choice": "Choose only if exactly one candidate passes both thresholds; otherwise abstain."},
        "games": games,
        "limitations": [
            "Thresholds were inspected on Swiss B70 before this three-recording run; results are development only.",
            "Bright clothing, graphics and pale flooring can mimic ice; a short delivery may fall between samples.",
            "A view with ice is not proof of a physical throw or of the correct counter association.",
            "No existing counter link or event count is changed by this diagnostic.",
        ],
    }


def main():
    payload = json.dumps(build(), indent=2) + "\n"
    if OUTPUT.exists():
        if OUTPUT.read_text() != payload:
            raise SystemExit("Existing ice tie-break audit differs from inputs or code")
        print(f"Verified {OUTPUT}")
    else:
        OUTPUT.write_text(payload)
        print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
