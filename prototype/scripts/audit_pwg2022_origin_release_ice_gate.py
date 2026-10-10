"""Post-transfer ice-context gate on frozen held-cap passages."""

import hashlib
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.origin_release_ice_support import passage_has_ice

TRANSFER = ROOT / "validation/official-shot-sequence/pwg2022-origin-release-transfer.json"
REFERENCE = ROOT / "validation/official-shot-sequence/pwg2022-official-shot-ledger.json"
OUTPUT = ROOT / "validation/official-shot-sequence/pwg2022-origin-release-ice-gate.json"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first post-transfer ice audit")
    transfer = json.loads(TRANSFER.read_text())
    reference = json.loads(REFERENCE.read_text())
    games = {game["official_game_code"]: game for game in reference["games"]}
    rows = []
    for code, game in games.items():
        if (
            transfer["input_hashes_by_game"][code]["source_video_sha256"]
            != game["source_video_sha256"]
        ):
            raise ValueError(f"Source video provenance mismatch: {code}")
        cap = cv2.VideoCapture(str(ROOT / game["source_video_path"]))
        if not cap.isOpened():
            raise RuntimeError(f"Cannot read {code} source")
        fps = cap.get(cv2.CAP_PROP_FPS)
        for source in transfer["rows"]:
            if source["official_game_code"] != code:
                continue
            accepted, rejected = [], []
            for passage in source["passages"]:
                time_s = passage["held_interval_s"][0]
                cap.set(cv2.CAP_PROP_POS_FRAMES, round(time_s * fps))
                ok, frame = cap.read()
                if not ok:
                    raise RuntimeError(f"Frame decode failed at {time_s}")
                supported, ice_fraction = passage_has_ice(frame, passage)
                audited = {
                    **passage,
                    "held_frame_time_s": time_s,
                    "below_ice_fraction": ice_fraction,
                }
                (accepted if supported else rejected).append(audited)
            rows.append(
                {
                    "official_game_code": code,
                    "shot_id": source["shot_id"],
                    "origin_interval_s": source["origin_interval_s"],
                    "accepted_passages": accepted,
                    "rejected_passages": rejected,
                    "unique_passage_colour": accepted[0]["colour"] if len(accepted) == 1 else None,
                }
            )
        cap.release()
    output = {
        "status": "postscore_ice_context_gate_on_frozen_held_cap_transfer_not_f1",
        "transfer_sha256": digest(TRANSFER),
        "official_reference_sha256": digest(REFERENCE),
        "ice_gate_code_sha256": digest(ROOT / "prototype/origin_release_ice_support.py"),
        "runner_sha256": digest(Path(__file__)),
        "rule": "For each previously emitted held-cap passage, sample its first held frame and require at least 60% low-saturation bright pixels in an 80×30 px region 20–50 px below the held centre; clipped regions abstain.",
        "scanned_window_count": len(rows),
        "accepted_passage_count": sum(len(row["accepted_passages"]) for row in rows),
        "rejected_passage_count": sum(len(row["rejected_passages"]) for row in rows),
        "rows": rows,
        "limitations": [
            "This gate was chosen after source review exposed a Swiss red-jacket false positive in the first held-cap transfer; the same three recordings are postscore development evidence.",
            "White clothing, bright boards or changed illumination may mimic ice; true throws near a cropped frame edge may be rejected.",
            "No independent complete-video throw-event precision or recall is established.",
        ],
    }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n")
    print(
        {
            key: output[key]
            for key in ("scanned_window_count", "accepted_passage_count", "rejected_passage_count")
        }
    )


if __name__ == "__main__":
    main()
