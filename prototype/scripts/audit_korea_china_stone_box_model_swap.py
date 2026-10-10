"""Compare frozen stone-box models on exposed Korea-China candidate windows."""

from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from scripts.audit_full_shot_cap_motion import tracks_for_shot  # noqa: E402
from stone_patch_detector import detect_stones, load_model  # noqa: E402

BASE = ROOT / "validation/throw-event-benchmark/paralympics-2022-korea-china"
SOURCE = BASE / "source.mp4"
LEDGER = (
    ROOT
    / "validation/curlobserver-learned-probe/korea-china-full-first-transfer/candidate-event-ledger.json"
)
OUTPUT = BASE / "STONE-BOX-MODEL-SWAP-PILOT.json"
MODELS = {
    "frozen_v1": ROOT / "validation/curlobserver-learned-probe/model-v1/model.npz",
    "public_tracking_v2": ROOT
    / "validation/curlobserver-learned-probe/public-tracking-v2/model.npz",
}
CONFLICT_IDS = ("T001", "T095", "T099", "T101")
CONTROL_IDS = ("T002", "T004", "T006", "T008", "T010")


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Selected model-swap pilot already exists")
    ledger = json.loads(LEDGER.read_text())
    source_hash = digest(SOURCE)
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    if source_hash != ledger["source_sha256"] or source_hash == reserved["source_sha256"]:
        raise ValueError("Source changed or reserved source selected")
    candidates = {row["candidate_id"]: row for row in ledger["events"]}
    ids = CONFLICT_IDS + CONTROL_IDS
    if len(candidates) != len(ledger["events"]) or any(cid not in candidates for cid in ids):
        raise ValueError("Selected candidate missing or duplicate IDs")
    models = {name: load_model(path) for name, path in MODELS.items()}
    cap = cv2.VideoCapture(str(SOURCE), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        raise RuntimeError("Cannot open source video")
    fps = cap.get(cv2.CAP_PROP_FPS)
    rows = []
    try:
        for cid in ids:
            candidate = candidates[cid]
            start, end = candidate["release_window_s"]
            observations = {name: {"red": [], "yellow": []} for name in models}
            box_counts = {name: {"red": 0, "yellow": 0} for name in models}
            samples = 0
            for tick in range(round(start * 2), round(end * 2)):
                time_s = round(tick / 2, 3)
                cap.set(cv2.CAP_PROP_POS_FRAMES, round(time_s * fps))
                ok, frame = cap.read()
                if not ok:
                    raise RuntimeError(f"Frame decode failed at {time_s}")
                samples += 1
                for name, model in models.items():
                    grouped = {"red": [], "yellow": []}
                    for box in detect_stones(frame, model):
                        x, y, width, height = box["bbox"]
                        grouped[box["colour"]].append(
                            {
                                "pixel": [x + width / 2, y + height / 2],
                                "bbox": box["bbox"],
                                "confidence": box["confidence"],
                            }
                        )
                        box_counts[name][box["colour"]] += 1
                    for colour in grouped:
                        observations[name][colour].append((time_s, grouped[colour]))
            rows.append(
                {
                    "candidate_id": cid,
                    "selection": "postscore_colour_conflict"
                    if cid in CONFLICT_IDS
                    else "counter_backed_red_control",
                    "shot_id": candidate["shot_id"],
                    "candidate_colour": candidate["colour"],
                    "counter_id": candidate["counter_id"],
                    "release_window_s": candidate["release_window_s"],
                    "sample_count": samples,
                    "models": {
                        name: {
                            "box_counts": box_counts[name],
                            "supported_tracks": tracks_for_shot(
                                observations[name], candidate["shot_id"]
                            ),
                        }
                        for name in models
                    },
                }
            )
            print(f"{cid} {samples} frames", flush=True)
    finally:
        cap.release()
    result = {
        "status": "selected_postscore_box_model_transfer_diagnostic_not_event_validation",
        "source_video_sha256": source_hash,
        "candidate_ledger_sha256": digest(LEDGER),
        "model_sha256": {name: digest(path) for name, path in MODELS.items()},
        "box_detector_code_sha256": digest(ROOT / "prototype/stone_patch_detector.py"),
        "tracking_code_sha256": digest(ROOT / "prototype/stone_motion_fallback.py"),
        "runner_sha256": digest(Path(__file__)),
        "sample_rate_hz": 2,
        "selection": {"conflicts": list(CONFLICT_IDS), "controls": list(CONTROL_IDS)},
        "rows": rows,
        "limitations": [
            "Nine exposed windows were selected after the first full-match result; this is not an independent test.",
            "Controls are counter-backed candidate windows, not manually verified stone-track labels.",
            "Image boxes and same-shot tracks do not prove a physical throw or cross-view identity.",
        ],
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
