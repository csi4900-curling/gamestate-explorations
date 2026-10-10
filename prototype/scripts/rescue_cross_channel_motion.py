"""Supplement isolated events agreed by learned-box and cap tracks."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256
from cross_channel_motion import cross_channel_pairs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--learned-raw", type=Path, required=True)
    parser.add_argument("--learned-screen", type=Path, required=True)
    parser.add_argument("--cap-raw", type=Path, required=True)
    parser.add_argument("--cap-screen", type=Path, required=True)
    parser.add_argument("--fused-screen", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve earlier result")
    learned = json.loads(args.learned_raw.read_text())
    learned_screen = json.loads(args.learned_screen.read_text())
    cap = json.loads(args.cap_raw.read_text())
    cap_screen = json.loads(args.cap_screen.read_text())
    fused = json.loads(args.fused_screen.read_text())
    if any(source["source_sha256"] != learned["source_sha256"]
           or source["source_interval_s"] != learned["source_interval_s"]
           for source in (learned_screen, cap, cap_screen, fused)):
        parser.error("Input source or interval differs")
    if (learned_screen["input_sha256"] != file_sha256(args.learned_raw)
            or cap_screen["input_sha256"] != file_sha256(args.cap_raw)
            or fused["input_sha256"] != file_sha256(args.learned_raw)):
        parser.error("Raw/screen fingerprints differ")
    pair_rows = cross_channel_pairs(
        learned["motion_candidates"], learned_screen["decisions"],
        cap["motion_candidates"], cap_screen["decisions"],
    )
    cap_by_id = {row["id"]: row for row in cap["motion_candidates"]}
    accepted = list(fused["corroborated_candidates"])
    supplemental = []
    withheld = []
    for pair in pair_rows:
        cap_track = cap_by_id[pair["cap_id"]]
        nearest = min(
            (abs(pair["crossing_time_s"] - other["crossing_time_s"])
             for other in accepted if other["gap_id"] == cap_track["gap_id"]),
            default=float("inf"),
        )
        if nearest <= 20:
            withheld.append({**pair, "reason": "accepted_event_within_20s"})
            continue
        extra = dict(cap_track, id="paired-cap:" + cap_track["id"],
                     evidence_channel="two_channel_motion_agreement",
                     corroborating_learned_id=pair["learned_id"],
                     pair_evidence=pair)
        accepted.append(extra)
        supplemental.append(extra)
    result = dict(fused)
    result.update({
        "status": "development_cross_channel_rescued_gap_candidates",
        "input_sha256": file_sha256(args.learned_raw),
        "fused_screen_sha256": file_sha256(args.fused_screen),
        "cap_raw_sha256": file_sha256(args.cap_raw),
        "cap_screen_sha256": file_sha256(args.cap_screen),
        "pair_model_sha256": file_sha256(ROOT / "prototype/cross_channel_motion.py"),
        "pair_runner_sha256": file_sha256(__file__),
        "cross_channel_pairs": pair_rows,
        "cross_channel_supplements": supplemental,
        "withheld_cross_channel_pairs": withheld,
        "corroborated_candidates": accepted,
    })
    result["limitations"] = fused["limitations"] + [
        "Two-channel agreement rule was fitted after inspecting the 900–1200 s miss.",
        "The two detectors share colour segmentation and video frames; agreement is not independent validation.",
    ]
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"pairs": len(pair_rows), "supplemented": len(supplemental),
                      "withheld": len(withheld)}))


if __name__ == "__main__":
    main()
