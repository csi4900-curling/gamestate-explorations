"""Transfer Latvia's frozen visual-cue pair to reviewed Estonia/Italy paths."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cap_patch_verifier import score_candidates
from right_context_tier import context_tier
from right_visual_cue_pair import visual_cue_pair
from stone_patch_detector import load_model

BASE = ROOT / "validation/throw-event-benchmark"
SOURCES = {
    "estonia": {
        "video": BASE / "canada-estonia-2024/source.mp4",
        "scan": BASE / "canada-estonia-2024/right-global-area-postscore.json",
        "review": BASE / "canada-estonia-2024/right-global-area-source-review/source-prefix-classes.json",
        "context": BASE / "canada-estonia-2024/right-global-area-combined-context-postscore.json",
        "ring": BASE / "canada-estonia-2024/right-global-area-ice-context-postscore.json",
        "underpoint": BASE / "canada-estonia-2024/right-global-area-underpoint-postscore.json",
    },
    "italy": {
        "video": BASE / "canada-italy/source.mp4",
        "scan": BASE / "canada-italy/right-global-area-fixed-transfer.json",
        "review": BASE / "canada-italy/right-global-area-source-review/source-prefix-classes.json",
        "context": BASE / "canada-italy/right-global-area-combined-context-transfer.json",
        "ring": BASE / "canada-italy/right-global-area-ice-context-transfer.json",
        "underpoint": BASE / "canada-italy/right-global-area-underpoint-transfer.json",
    },
}
MODEL = ROOT / "validation/curlobserver-learned-probe/sideview-patch-transfer-v1/model.npz"
OUT = BASE / "right-visual-cue-pair-estonia-italy-development.json"
CONTEXT_CLASS_NAMES = {
    "moving_stone": "moving_stone_prefix",
    "person_or_wheelchair": "person_or_equipment_prefix",
    "stone_pixels_identity_uncertain": "stone_pixels_identity_uncertain",
}


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def main():
    model = load_model(MODEL)
    if float(model["threshold"]) != 0:
        raise ValueError("Frozen model threshold changed")
    rows = []
    input_hashes = {"model": digest(MODEL)}
    for recording, paths in SOURCES.items():
        scan = json.loads(paths["scan"].read_text())
        review = json.loads(paths["review"].read_text())
        context = json.loads(paths["context"].read_text())
        video_hash = digest(paths["video"])
        if (scan["source_sha256"] != video_hash or
                review["source_sha256"] != video_hash or
                review["probe_sha256"] != digest(paths["scan"]) or
                context["ring_review_threshold"] != 0.25 or
                context["underpoint_review_threshold"] != 0.25 or
                len(context["pairs"]) != 1 or
                context["pairs"][0]["ring_score_sha256"] != digest(paths["ring"]) or
                context["pairs"][0]["underpoint_score_sha256"] != digest(
                    paths["underpoint"])):
            raise ValueError(f"{recording} source or frozen context differs")
        by_scan = {row["raw_track_id"]: row for row in scan[
            "directional_review_proposals"]}
        by_context = {row["raw_track_id"]: row for row in context["rows"]}
        if (len(by_scan) != len(scan["directional_review_proposals"]) or
                len(by_context) != len(context["rows"]) or
                set(by_scan) != set(by_context) or
                set(by_context) != {
                    row["raw_track_id"] for row in review["rows"]}):
            raise ValueError(f"{recording} reviewed proposal coverage differs")
        capture = cv2.VideoCapture(str(paths["video"]), cv2.CAP_FFMPEG,
                                   [cv2.CAP_PROP_N_THREADS, 1])
        fps = capture.get(cv2.CAP_PROP_FPS)
        if not capture.isOpened() or fps <= 0:
            raise ValueError(f"{recording} source unreadable")
        try:
            for reviewed in review["rows"]:
                track = reviewed["raw_track_id"]
                proposal = by_scan[track]
                cue = by_context[track]
                stored_context_tier = ("context_cluttered_review" if cue[
                    "combined_review_tier"] == "cluttered_review" else cue[
                        "combined_review_tier"])
                if (cue["source_prefix_class"] != CONTEXT_CLASS_NAMES[
                        reviewed["source_prefix_class"]] or stored_context_tier !=
                        context_tier(cue["ring_nonice_fraction"],
                                     cue["underpoint_nonice_fraction"],
                                     threshold=0.25)):
                    raise ValueError(f"{recording}:{track} cue/review mismatch")
                points = {p["time_s"]: p for p in proposal[
                    "observed_prefix_points"]}
                samples = []
                for time in reviewed["sample_source_times_s"]:
                    if time not in points:
                        raise ValueError(f"{recording}:{track} source point absent")
                    capture.set(cv2.CAP_PROP_POS_FRAMES, round(time * fps))
                    ok, frame = capture.read()
                    if not ok or frame.shape[:2] != (360, 640):
                        raise ValueError(f"{recording}:{track} frame unreadable")
                    scored = score_candidates(frame, [{"bbox": points[time][
                        "bbox"]}], model)[0]
                    samples.append({"time_s": time,
                                    "cap_bbox_px": points[time]["bbox"],
                                    "patch_score": round(scored["patch_score"], 6),
                                    "patch_accepted": scored["patch_accepted"]})
                if len(samples) != 3:
                    raise ValueError(f"{recording}:{track} sample count changed")
                patch_positive = any(s["patch_accepted"] for s in samples)
                rows.append({
                    "recording": recording,
                    "raw_track_id": track,
                    "source_prefix_class": reviewed["source_prefix_class"],
                    "context_tier": stored_context_tier,
                    "ring_nonice_fraction": cue["ring_nonice_fraction"],
                    "underpoint_nonice_fraction": cue["underpoint_nonice_fraction"],
                    "patch_samples": samples,
                    "any_positive_patch": patch_positive,
                    "visual_cue_pair_review_tier": visual_cue_pair(
                        stored_context_tier, patch_positive),
                    "physical_throw_verified": False,
                })
        finally:
            capture.release()
        input_hashes[recording] = {name: digest(path) for name, path in
                                   paths.items()}
    counts = Counter((row["recording"], row["source_prefix_class"],
                      row["visual_cue_pair_review_tier"]) for row in rows)
    result = {
        "status": "frozen_cross_match_visual_cue_pair_source_pixel_transfer_not_event_truth",
        "input_sha256": input_hashes,
        "feature_code_sha256": digest(ROOT / "prototype/stone_patch_detector.py"),
        "patch_scorer_code_sha256": digest(ROOT / "prototype/cap_patch_verifier.py"),
        "cue_pair_code_sha256": digest(ROOT / "prototype/right_visual_cue_pair.py"),
        "context_tier_code_sha256": digest(ROOT / "prototype/right_context_tier.py"),
        "runner_sha256": digest(Path(__file__)),
        "frozen_context_threshold": 0.25,
        "frozen_patch_threshold": 0.0,
        "reviewed_path_count": len(rows),
        "counts_by_recording_class_tier": {
            recording: {cls: {tier: counts[recording, cls, tier]
                              for tier in ("both_visual_cues_positive_review",
                                           "visual_cues_disagree_review",
                                           "both_visual_cues_weak_review",
                                           "context_unavailable_review")}
                        for cls in sorted({row["source_prefix_class"] for row in
                                           rows if row["recording"] == recording})}
            for recording in SOURCES},
        "rows": rows,
        "limitations": [
            "These 36 previously exposed source-reviewed paths are selected and not independent physical throw labels.",
            "A short source-pixel class does not verify a delivery, complete track identity, release or settle.",
            "Frozen cue agreement and disagreement only organize review; no physical throw is accepted or rejected.",
            "The recordings share broadcast style and do not prove cross-production generalization or event F1.",
        ],
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"paths": len(rows),
                      "by_recording": {name: sum(row["recording"] == name
                                                for row in rows)
                                       for name in SOURCES}}))


if __name__ == "__main__":
    main()
