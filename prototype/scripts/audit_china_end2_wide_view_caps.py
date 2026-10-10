"""Preserve image-space stone evidence in a wide elliptical-house camera view."""

from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "prototype"))
from prototype.image_space_stone_cluster import stable_image_caps
from prototype.video_board_observation import blue_ring_mask
from prototype.stone_motion_fallback import stone_cap_candidates
from prototype.cap_patch_verifier import score_candidates
from prototype.stone_patch_detector import load_model

BASE = ROOT / "validation/official-shot-sequence"
VIDEO = ROOT / "validation/throw-event-benchmark/paralympics-2022-canada-china/source.mp4"
MODEL = ROOT / "validation/curlobserver-learned-probe/cap-patch-crossmatch-v1/model-excluding-swiss-transfer.npz"
PRIOR = BASE / "china-end2-adjacent-video-boards-first.json"
OUTPUT = BASE / "china-end2-wide-perspective-cap-evidence-development.json"
TIMES_S = (1632, 1636, 1640, 1644)


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def wide_house_ellipse(frame):
    mask = blue_ring_mask(frame).astype("uint8") * 255
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL,
                                   cv2.CHAIN_APPROX_SIMPLE)
    options = []
    for contour in contours:
        x, y, width, height = cv2.boundingRect(contour)
        if (width < 250 or height < 70 or width / height < 2
                or not 180 <= x + width / 2 <= 460 or y < 180
                or len(contour) < 5):
            continue
        center, axes, angle = cv2.fitEllipse(contour)
        options.append((cv2.contourArea(contour), {
            "center_px": [round(value, 2) for value in center],
            "axis_lengths_px": [round(value, 2) for value in axes],
            "angle_degrees": round(angle, 2),
            "component_bbox_px": [x, y, width, height],
            "coordinate_status": "uncalibrated_perspective_ellipse",
        }))
    return max(options, key=lambda item: item[0])[1] if options else None


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first wide-view diagnostic")
    prior = json.loads(PRIOR.read_text())
    source_hash = digest(VIDEO)
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    if source_hash != prior["source_sha256"] or source_hash == reserved["source_sha256"]:
        raise ValueError("Source mismatch or reserved source selected")
    model = load_model(MODEL)
    capture = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG,
                               [cv2.CAP_PROP_N_THREADS, 1])
    fps = capture.get(cv2.CAP_PROP_FPS)
    frames = []
    for time_s in TIMES_S:
        capture.set(cv2.CAP_PROP_POS_FRAMES, round(time_s * fps))
        ok, frame = capture.read()
        if not ok:
            raise RuntimeError(f"Cannot decode {time_s} s")
        resized = cv2.resize(frame, (640, 360))
        ellipse = wide_house_ellipse(resized)
        candidates = []
        for colour in ("red", "yellow"):
            raw = stone_cap_candidates(frame, colour,
                                       allow_bright_body=True,
                                       allow_large_caps=True)
            candidates.extend({"colour": colour, "pixel": item["pixel"],
                               "patch_score": round(item["patch_score"], 3)}
                              for item in score_candidates(frame, raw, model)
                              if item["patch_score"] >= -0.6)
        frames.append({"time_s": time_s, "ellipse": ellipse,
                       "candidates": candidates})
    capture.release()
    stable = stable_image_caps(frames)
    output = {
        "status": "postscore_wide_view_image_space_stone_evidence_not_calibrated_board",
        "source_sha256": source_hash,
        "prior_adjacent_scan_sha256": digest(PRIOR),
        "model_sha256": digest(MODEL),
        "cap_verifier_sha256": digest(ROOT / "prototype/cap_patch_verifier.py"),
        "cluster_code_sha256": digest(ROOT / "prototype/image_space_stone_cluster.py"),
        "runner_sha256": digest(Path(__file__)),
        "selected_times_s": list(TIMES_S),
        "frames": frames,
        "stable_image_caps": stable,
        "limitations": [
            "Times were selected after seeing the China adjacent-board coverage failure.",
            "Image-space cap patches are not calibrated house or ice coordinates.",
            "The elliptical camera view may have perspective distortion and occlusion.",
            "No stone identity or cross-view match is established.",
        ],
    }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n")
    print({"frames": len(frames), "ellipses": sum(row["ellipse"] is not None
                                                  for row in frames),
           "stable_caps": [(row["colour"], row["pixel_center"])
                           for row in stable]})


if __name__ == "__main__":
    main()
