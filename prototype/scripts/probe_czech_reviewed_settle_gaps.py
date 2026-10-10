"""Inventory source-pixel cap ambiguity between moving paths and partial boards."""

from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from local_colour_cap_probe import local_cap_components  # noqa: E402

BASE = ROOT / "validation/throw-event-benchmark/canada-czech-2024"
VIDEO = BASE / "source-1080p-full-format270.mp4"
GAPS = BASE / "full-reviewed-stone-replay-gaps-development.json"
BOARDS = BASE / "full-match-partial-boards-postscore.json"
OUT = BASE / "full-reviewed-settle-gap-cap-inventory-development.json"


def digest(path):
    h = sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def sample_indices(start_s, end_s, fps):
    """Include 2 Hz interior samples and exact endpoint frames."""
    start = round(start_s * fps)
    end = round(end_s * fps)
    step = round(fps / 2)
    return sorted(set(range(start, end + 1, step)) | {end})


def roi_for_points(points, shape, margin=65):
    height, width = shape
    x0 = max(0, int(min(p[0] for p in points) - margin))
    y0 = max(0, int(min(p[1] for p in points) - margin))
    x1 = min(width, int(max(p[0] for p in points) + margin + 1))
    y1 = min(height, int(max(p[1] for p in points) + margin + 1))
    if x0 >= x1 or y0 >= y1:
        raise ValueError("Invalid source-pixel gap ROI")
    return (x0, y0, x1, y1)


def main():
    if OUT.exists():
        raise ValueError("Settle-gap cap inventory already exists")
    gaps, boards = (json.loads(p.read_text()) for p in (GAPS, BOARDS))
    source_hash = digest(VIDEO)
    if source_hash != boards["high_resolution_source_sha256"]:
        raise ValueError("Board and high-resolution source differ")
    board_by_id = {r["candidate_id"]: r for r in boards["rows"]}
    cap = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    fps = cap.get(cv2.CAP_PROP_FPS)
    if not cap.isOpened() or abs(fps - 30) > 0.01:
        raise ValueError("High-resolution source unreadable or FPS changed")
    rows = []
    try:
        for gap in gaps["rows"]:
            path = gap["observed_left_motion_path"]
            board_time = gap["first_same_colour_local_observation_s"]
            if not path or board_time is None:
                continue
            start_time = path[-1]["source_time_s"]
            if not 0 < board_time - start_time <= 6:
                raise ValueError(f"Unexpected gap duration: {gap['episode_id']}")
            board = board_by_id[gap["left_motion_candidate_id"]]
            first_frame = next(f for f in board["frames"] if f["source_time_s"] == board_time)
            board_centers = [
                s["pixel_center"]
                for s in first_frame["stones"]
                if s["colour"] == gap["colour_claim"]
            ]
            if not board_centers:
                raise ValueError("Missing first same-colour board center")
            endpoint = path[-1]["pixel_center_1080"]
            roi = roi_for_points([endpoint] + board_centers, (1080, 1920))
            samples = []
            for index in sample_indices(start_time, board_time, fps):
                cap.set(cv2.CAP_PROP_POS_FRAMES, index)
                ok, frame = cap.read()
                if not ok or frame.shape[:2] != (1080, 1920):
                    raise ValueError(f"Unreadable source frame {index}")
                samples.append(
                    {
                        "source_time_s": round(index / fps, 6),
                        "decoded_frame_index": index,
                        "same_colour_components": local_cap_components(
                            frame, roi, gap["colour_claim"]
                        ),
                    }
                )
            rows.append(
                {
                    "episode_id": gap["episode_id"],
                    "left_motion_candidate_id": gap["left_motion_candidate_id"],
                    "colour_claim": gap["colour_claim"],
                    "last_motion_time_s": start_time,
                    "first_same_colour_board_time_s": board_time,
                    "last_motion_center_px_1080": endpoint,
                    "first_same_colour_board_centers_px_1080": board_centers,
                    "roi_xyxy_px_1080": list(roi),
                    "single_component_sample_count": sum(
                        len(s["same_colour_components"]) == 1 for s in samples
                    ),
                    "ambiguous_sample_count": sum(
                        len(s["same_colour_components"]) != 1 for s in samples
                    ),
                    "samples": samples,
                    "persistent_stone_identity_verified": False,
                    "simulation_ready": False,
                }
            )
    finally:
        cap.release()
    result = {
        "status": "development_source_pixel_gap_inventory_not_identity_validation",
        "source_video_sha256": source_hash,
        "input_sha256": {"replay_gaps": digest(GAPS), "boards": digest(BOARDS)},
        "runner_sha256": digest(Path(__file__)),
        "component_code_sha256": digest(ROOT / "prototype/local_colour_cap_probe.py"),
        "method": {
            "source_resolution_px": [1920, 1080],
            "fps": fps,
            "sampling": "last moving-path frame, every 0.5 s, exact first same-colour board frame",
            "roi": "bounding rectangle of last path center and all same-colour first-board centers, expanded by 65 px",
            "colour_component_policy": "same HSV masks and 20 px² minimum as E019 10 Hz probe; preserve all components",
            "unique_component_is_identity": False,
        },
        "eligible_gap_count": len(rows),
        "any_ambiguous_sample_gap_count": sum(r["ambiguous_sample_count"] > 0 for r in rows),
        "rows": rows,
        "limitations": [
            "The source-reviewed prefixes, moving paths and first partial boards are same-agent development evidence, not independent physical identity ground truth.",
            "ROI geometry uses the later same-colour board proposals and can include unrelated stones; component count is a visibility diagnostic, not an association decision.",
            "A single colour component does not establish the same physical stone, particularly between sparse 0.5-second samples or during collisions.",
            "ROI and HSV settings were developed on this source. No transfer, metric accuracy, physical F1, complete game state or simulation readiness follows.",
        ],
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                "eligible_gaps": len(rows),
                "gaps_with_ambiguous_samples": result["any_ambiguous_sample_gap_count"],
                "samples": sum(len(r["samples"]) for r in rows),
            }
        )
    )


if __name__ == "__main__":
    main()
