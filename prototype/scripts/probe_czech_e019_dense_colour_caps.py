"""Measure local cap pixels through E019 contact without assigning identity."""

from hashlib import sha256
import json
from math import dist
from pathlib import Path
import sys

import cv2
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from local_colour_cap_probe import local_cap_components  # noqa: E402

BASE = ROOT / "validation/throw-event-benchmark/canada-czech-2024"
VIDEO = BASE / "source-1080p-full-format270.mp4"
MOTION = BASE / "full-match-motion-merged-postscore.json"
BOARD = BASE / "full-match-partial-boards-postscore.json"
AUDIT = BASE / "e019-settle-continuity-source-audit.json"
OUT = BASE / "e019-dense-colour-cap-probe"
ROI = (1300, 360, 1420, 530)
FRAME_INDICES = tuple(range(20580, 20641, 3))


def digest(path):
    h = sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def unique_center(row, colour):
    components = row[f"{colour}_components"]
    return components[0]["centroid_px_1080"] if len(components) == 1 else None


def main():
    if OUT.exists():
        raise ValueError("E019 dense cap probe already exists")
    motion = json.loads(MOTION.read_text())
    boards = json.loads(BOARD.read_text())
    audit = json.loads(AUDIT.read_text())
    video_hash = digest(VIDEO)
    if (motion["high_resolution_source_sha256"] != video_hash or
            boards["high_resolution_source_sha256"] != video_hash or
            audit["source_video_sha256"] != video_hash):
        raise ValueError("E019 source lineage differs")
    path = next(r for r in motion["rows"] if r["candidate_id"] == "S20")[
        "selection"]["path"]
    path_by_time = {p["source_time_s"]: p["pixel_center"] for p in path}
    board = next(r for r in boards["rows"] if r["candidate_id"] == "S20")
    board_red_by_time = {
        frame["source_time_s"]: [s["pixel_center"] for s in frame["stones"]
                                 if s["colour"] == "red"]
        for frame in board["frames"]
    }
    capture = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG,
                               [cv2.CAP_PROP_N_THREADS, 1])
    fps = capture.get(cv2.CAP_PROP_FPS)
    if not capture.isOpened() or abs(fps - 30) > 0.01:
        raise ValueError("E019 source unreadable or frame rate changed")
    samples = []
    try:
        for index in FRAME_INDICES:
            capture.set(cv2.CAP_PROP_POS_FRAMES, index)
            ok, frame = capture.read()
            if not ok or frame.shape[:2] != (1080, 1920):
                raise ValueError(f"E019 source frame unreadable: {index}")
            samples.append({
                "source_time_s": round(index / fps, 6),
                "decoded_frame_index": index,
                "red_components": local_cap_components(frame, ROI, "red"),
                "yellow_components": local_cap_components(frame, ROI, "yellow"),
            })
    finally:
        capture.release()
    by_time = {s["source_time_s"]: s for s in samples}
    anchors = []
    for time, kind, expected in (
            (686.0, "moving_path", path_by_time[686.0]),
            (686.5, "moving_path", path_by_time[686.5]),
            (687.0, "partial_board", board_red_by_time[687.0][0]),
            (688.0, "partial_board", board_red_by_time[688.0][0])):
        measured = unique_center(by_time[time], "red")
        anchors.append({"source_time_s": time, "stored_stage": kind,
                        "stored_red_center_px_1080": expected,
                        "local_red_cap_center_px_1080": measured,
                        "center_distance_px_1080": round(dist(expected, measured), 3)
                        if measured else None})
    result = {
        "status": "same_agent_local_source_pixel_measurement_not_physical_identity_truth",
        "episode_id": "E019", "left_candidate_id": "S20",
        "source_video_sha256": video_hash,
        "input_sha256": {"motion": digest(MOTION), "board": digest(BOARD),
                         "visual_audit": digest(AUDIT)},
        "runner_sha256": digest(Path(__file__)),
        "component_code_sha256": digest(ROOT / "prototype/local_colour_cap_probe.py"),
        "method": {
            "source_resolution_px": [1920, 1080], "fps": fps,
            "sample_interval_s": 0.1,
            "roi_xyxy_px_1080": list(ROI),
            "red_hsv_opencv": "(H<12 or H>170) and S>85 and V>50",
            "yellow_hsv_opencv": "16<H<43 and S>85 and V>70",
            "minimum_contour_area_px2": 20,
            "component_policy": "retain every contour; unique center only if exactly one component",
        },
        "sample_count": len(samples),
        "red_unique_component_frames": sum(len(s["red_components"]) == 1
                                           for s in samples),
        "yellow_ambiguous_frame_times_s": [s["source_time_s"] for s in samples
                                           if len(s["yellow_components"]) != 1],
        "stored_stage_anchor_comparisons": anchors,
        "samples": samples,
        "physical_throw_identity_independently_verified": False,
        "full_contact_dynamics_reconstructed": False,
        "simulation_ready": False,
        "limitations": [
            "The local ROI and HSV thresholds were chosen after inspecting E019; this is a development probe, not transfer validation.",
            "Cap centroid is not a physical stone center; occlusion and overlap can shift or split colour components.",
            "One contour does not prove persistent physical identity, and ambiguous yellow frames are left unresolved.",
            "Image-pixel motion alone does not determine stone spin, collision impulse, metric speed or complete game state.",
        ],
    }
    OUT.mkdir(parents=True)
    (OUT / "measurements.json").write_text(json.dumps(result, indent=2) + "\n")
    fig, ax = plt.subplots(figsize=(10, 5.5), layout="constrained")
    for colour, marker in (("red", "o"), ("yellow", "s")):
        points = [(s["source_time_s"], unique_center(s, colour))
                  for s in samples]
        x = [t for t, _ in points]
        y = [center[1] if center is not None else float("nan")
             for _, center in points]
        ax.plot(x, y, marker=marker, label=f"{colour} unique cap component",
                color=colour if colour == "red" else "#c89000")
    for t in result["yellow_ambiguous_frame_times_s"]:
        ax.axvspan(t - 0.035, t + 0.035, color="#c89000", alpha=0.14)
    ax.set(xlabel="Source video time (s)", ylabel="Cap centroid y (1080p image pixels)",
           title="E019 local colour-cap positions through contact")
    ax.invert_yaxis()
    ax.grid(alpha=0.25)
    ax.legend(loc="best")
    fig.savefig(OUT / "cap-centroids.png", dpi=170)
    plt.close(fig)
    print(json.dumps({"samples": len(samples),
                      "red_unique": result["red_unique_component_frames"],
                      "yellow_ambiguous_times": result[
                          "yellow_ambiguous_frame_times_s"],
                      "output": str(OUT)}))


if __name__ == "__main__":
    main()
