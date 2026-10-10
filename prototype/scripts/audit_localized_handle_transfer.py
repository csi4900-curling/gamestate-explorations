"""Check conservative local handle recentering on the seven yellow transfers."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
sys.path.insert(0, str(ROOT / "prototype/scripts"))
from handle_localization import locate_yellow_handle  # noqa: E402
from probe_t11_handle_periodicity import mask_series, normalized_yellow_mask  # noqa: E402
from probe_t11_handle_polarity import (TEMPLATE_LEFT_S, TEMPLATE_RIGHT_S,
                                       polarity)  # noqa: E402

VIDEO = ROOT / "prototype/throw-analysis/end3.mp4"
SOURCE_META = ROOT / "prototype/throw-analysis/source.json"
CROSS_VIEW = ROOT / "prototype/cross-view/results.json"
PRIOR = ROOT / "validation/spin-observability/T11-template-yellow-transfer.json"
OUTPUT = ROOT / "validation/spin-observability/T11-localized-handle-transfer.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Localized handle-transfer audit already exists")
    prior = json.loads(PRIOR.read_text())
    crossview = json.loads(CROSS_VIEW.read_text())
    meta = json.loads(SOURCE_META.read_text())
    if (digest(VIDEO) != prior["source_video_sha256"] or
            digest(CROSS_VIEW) != prior["cross_view_results_sha256"]):
        raise ValueError("Prior transfer source differs")
    cap = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG,
                           [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        raise RuntimeError("Cannot open source video")
    rows = []
    try:
        t11 = next(row for row in crossview["throws"] if row["id"] == "T11")
        times = np.round(np.arange(2307.0, 2312.51, 0.1), 3)
        masks, retained = mask_series(cap, t11, times,
                                      meta["source_interval_s"][0])
        if len(retained) != len(times):
            raise RuntimeError("T11 template masks unavailable")
        by_time = {t: i for i, t in enumerate(retained)}
        left = np.mean(masks[[by_time[t] for t in TEMPLATE_LEFT_S]], axis=0)
        right = np.mean(masks[[by_time[t] for t in TEMPLATE_RIGHT_S]], axis=0)
        for original in prior["rows"]:
            samples = []
            for sample in original["samples"]:
                t = sample["time_s"]
                x, y = sample["track_pixel"]
                cap.set(cv2.CAP_PROP_POS_MSEC,
                        (t - meta["source_interval_s"][0]) * 1000)
                ok, frame = cap.read()
                if not ok:
                    raise RuntimeError(f"Frame decode failed at {t}")
                location = locate_yellow_handle(frame, x, y)
                score = None
                clipped = None
                if location["center_pixel"] is not None:
                    new_x, new_y = location["center_pixel"]
                    left_roi, _, width, _ = location["component_bounds_in_roi"]
                    min_in_crop = (x - 80 + left_roi) - (new_x - 40)
                    max_in_crop = min_in_crop + width - 1
                    clipped = bool(min_in_crop <= 2 or max_in_crop >= 77)
                    if not clipped:
                        mask = normalized_yellow_mask(frame, new_x, new_y)
                        if mask is not None:
                            score = polarity(mask, left, right)
                samples.append({"time_s": t,
                                "original_crop_edge": sample[
                                    "yellow_component_at_crop_edge"],
                                "localization": location,
                                "localized_crop_edge": clipped,
                                "localized_polarity": score})
            counts = Counter(s["localization"]["status"] for s in samples)
            rows.append({"throw_id": original["throw_id"],
                         "sample_count": len(samples),
                         "original_edge_clipped_count": original["edge_clipped_count"],
                         "localization_status_counts": dict(counts),
                         "localized_edge_clipped_count": sum(
                             s["localized_crop_edge"] is True for s in samples),
                         "localized_polarity_count": sum(
                             s["localized_polarity"] is not None for s in samples),
                         "samples": samples})
            print(original["throw_id"], dict(counts), flush=True)
    finally:
        cap.release()
    result = {
        "status": "development_local_handle_observability_not_spin_count",
        "source_video_sha256": digest(VIDEO),
        "prior_transfer_sha256": digest(PRIOR),
        "localization_code_sha256": digest(ROOT / "prototype/handle_localization.py"),
        "mask_extraction_code_sha256": digest(ROOT / "prototype/scripts/probe_t11_handle_periodicity.py"),
        "runner_sha256": digest(Path(__file__)),
        "rows": rows,
        "limitations": [
            "One nearby yellow component is not proven to be the delivered stone; multiple components force abstention.",
            "Recentered crop quality does not calibrate the T11 pose template for other views or scales.",
            "The source track and all seven transfers are from one exposed recording; no full-throw revolution count is inferred.",
        ],
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
