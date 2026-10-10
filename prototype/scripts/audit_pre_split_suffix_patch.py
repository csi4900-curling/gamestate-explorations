"""Score suffix-added board objects with the unchanged cap-patch model."""

import argparse
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256  # noqa: E402
from cap_patch_verifier import score_candidates  # noqa: E402
from stone_patch_detector import load_model  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("video", "shapes", "model", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Suffix patch audit already exists")
    shapes = json.loads(args.shapes.read_text())
    if shapes["input_sha256"]["video"] != file_sha256(args.video):
        parser.error("Source video differs")
    model = load_model(args.model)
    capture = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG,
                               [cv2.CAP_PROP_N_THREADS, 1])
    if not capture.isOpened():
        parser.error("Cannot open video")
    fps = capture.get(cv2.CAP_PROP_FPS)
    rows = []
    try:
        for row in shapes["rows"]:
            if not row["added_by_suffix"]:
                continue
            t = row["source_time_s"]
            capture.set(cv2.CAP_PROP_POS_FRAMES, round(t * fps))
            ok, frame = capture.read()
            if not ok:
                raise RuntimeError(f"Cannot decode {t}")
            bbox = [value / 3 for value in row["bbox"]]
            result = score_candidates(frame, [{"bbox": bbox}], model)[0]
            rows.append({"candidate_id": row["candidate_id"],
                         "local_observation_id": row["local_observation_id"],
                         "source_time_s": t,
                         "bbox_1080p": row["bbox"],
                         "patch_score": result["patch_score"],
                         "patch_accepted": result["patch_accepted"]})
    finally:
        capture.release()
    output = {
        "status": "postscore_suffix_added_patch_diagnostic_not_board_validation",
        "video_sha256": file_sha256(args.video),
        "shapes_sha256": file_sha256(args.shapes),
        "model_sha256": file_sha256(args.model),
        "runner_sha256": file_sha256(Path(__file__)),
        "rows": rows,
        "limitations": [
            "Only two suffix-added objects are scored; they were selected after source inspection.",
            "A negative patch score cannot disprove a real stone, and a positive score cannot prove one.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print([(row["candidate_id"], round(row["patch_score"], 3),
            row["patch_accepted"]) for row in rows])


if __name__ == "__main__":
    main()
