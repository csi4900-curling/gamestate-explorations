"""Apply Latvia-developed 1080p underpoint tiers to Czech reviewed prefixes."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
from statistics import median
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from highres_underpoint_context import (  # noqa: E402
    review_tier,
    underpoint_nonice_fraction,
)

BASE = ROOT / "validation/throw-event-benchmark/canada-czech-2024"
LATVIA = ROOT / "validation/throw-event-benchmark/canada-latvia-2024"
VIDEO = BASE / "source-1080p-full-format270.mp4"
ALIGNMENT = BASE / "full-match-highres-alignment-postscore.json"
SCORES = BASE / "full-right-source-diverse-patch-transfer-development.json"
POSITIVE = BASE / "full-linked-positive-patch-pixel-audit.json"
NEGATIVE = BASE / "full-right-only-source-diverse-pixel-audit.json"
FROZEN = LATVIA / "end6-highres-underpoint-context-development.json"
OUT = BASE / "full-source-reviewed-highres-underpoint-latvia-rule-transfer-development.json"


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def main():
    if OUT.exists():
        raise ValueError("Czech high-resolution underpoint transfer exists")
    alignment, scores, positive, negative, frozen = (
        json.loads(p.read_text()) for p in (ALIGNMENT, SCORES, POSITIVE, NEGATIVE, FROZEN)
    )
    source_hash = digest(VIDEO)
    source_360_hash = scores["source_video_sha256"]
    code_hash = digest(ROOT / "prototype/highres_underpoint_context.py")
    if (
        source_hash != alignment["interval_video_sha256"]
        or source_360_hash != alignment["full_video_sha256"]
        or source_360_hash != positive["source_video_sha256"]
        or source_360_hash != negative["source_video_sha256"]
        or not alignment["all_best_at_zero_adjustment"]
        or alignment["source_offset_s"] != 0
        or code_hash != frozen["feature_code_sha256"]
    ):
        raise ValueError("Czech source alignment or Latvia-frozen rule differs")
    by_id = {r["right_proposal_id"]: r for r in scores["rows"]}
    if len(by_id) != len(scores["rows"]):
        raise ValueError("Duplicate right proposal")
    selected = positive["rows"] + negative["rows"]
    if len(selected) != 43 or len({r["right_proposal_id"] for r in selected}) != 43:
        raise ValueError("Reviewed Czech prefix inventory differs")
    capture = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not capture.isOpened():
        raise ValueError("Czech source unreadable")
    fps = capture.get(cv2.CAP_PROP_FPS)
    rows = []
    try:
        for reviewed in selected:
            pid = reviewed["right_proposal_id"]
            proposal = by_id[pid]
            sample_times = [p["time_s"] for p in proposal["samples"]]
            if sample_times != reviewed["source_sample_times_s"]:
                raise ValueError(f"Czech review time mismatch: {pid}")
            samples = []
            for point in proposal["samples"]:
                x, y, width, height = point["cap_bbox_px"]
                center = [3 * (x + width / 2), 3 * (y + height / 2)]
                index = round(point["time_s"] * fps)
                capture.set(cv2.CAP_PROP_POS_FRAMES, index)
                ok, frame = capture.read()
                if not ok:
                    raise ValueError(f"Czech frame {index} unreadable")
                score = underpoint_nonice_fraction(frame, center)
                samples.append(
                    {
                        "source_time_s": point["time_s"],
                        "decoded_frame_index": index,
                        "scaled_cap_center_1080p_px": center,
                        "underpoint_nonice_fraction": (None if score is None else round(score, 4)),
                    }
                )
            available = [
                s["underpoint_nonice_fraction"]
                for s in samples
                if s["underpoint_nonice_fraction"] is not None
            ]
            middle = round(median(available), 4) if available else None
            rows.append(
                {
                    "right_proposal_id": pid,
                    "source_pixel_class_for_audit_only": reviewed["sampled_source_pixel_class"],
                    "median_underpoint_nonice_fraction": middle,
                    "available_sample_count": len(available),
                    "review_tier": review_tier(middle),
                    "samples": samples,
                    "physical_throw_verified": False,
                }
            )
            print(pid, rows[-1]["review_tier"], middle, flush=True)
    finally:
        capture.release()
    counts = Counter((r["source_pixel_class_for_audit_only"], r["review_tier"]) for r in rows)
    payload = {
        "status": "latvia_developed_1080p_underpoint_czech_source_review_transfer_not_throw_truth",
        "source_video_sha256": source_hash,
        "source_360p_sha256": source_360_hash,
        "input_sha256": {
            "alignment": digest(ALIGNMENT),
            "scores": digest(SCORES),
            "positive_source_review": digest(POSITIVE),
            "negative_source_review": digest(NEGATIVE),
            "latvia_frozen_underpoint": digest(FROZEN),
        },
        "feature_code_sha256": code_hash,
        "runner_sha256": digest(Path(__file__)),
        "method": "Unchanged Latvia-developed 1080p underpoint HSV and 0.05/0.25 review tiers; Czech 360p source-reviewed cap-bbox centers scaled 3x using verified zero-offset full-1080p alignment; no label-dependent score choices.",
        "pixel_semantics_difference": "Czech center is a scaled coloured cap bbox, while Latvia center was a high-resolution body-template center; fractions are not identical physical patches.",
        "reviewed_path_count": len(rows),
        "tier_counts_by_source_class": {
            cls: {
                tier: counts[(cls, tier)]
                for tier in (
                    "clear_context_review",
                    "ambiguous_context_review",
                    "cluttered_context_review",
                    "context_unavailable",
                )
            }
            for cls in sorted({r["source_pixel_class_for_audit_only"] for r in rows})
        },
        "rows": rows,
        "limitations": [
            "Czech and Latvia are exposed 2024 broadcasts with similar split layouts, not independent event ground truth.",
            "Source-pixel classes are same-agent review of selected prefixes; no exhaustive false-positive or missed-throw inventory exists.",
            "Context can be misleading around white jerseys, paint, occlusion or frame boundaries; review tier is not a hard throw decision.",
            "Czech uses a scaled cap center and Latvia a body center, so the sampled support bands differ by the cap-to-body offset.",
        ],
    }
    OUT.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps({"paths": len(rows), "tiers": payload["tier_counts_by_source_class"]}))


if __name__ == "__main__":
    main()
