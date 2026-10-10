"""Measure a signed side-view handle silhouette sequence for T11.

This tests a visible left/right/left image cycle, not a physical revolution
count or an angular phase calibrated to the ice coordinate system.
"""

from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype/scripts"))
from probe_t11_handle_periodicity import mask_series  # noqa: E402

VIDEO = ROOT / "prototype/throw-analysis/end3.mp4"
SOURCE_META = ROOT / "prototype/throw-analysis/source.json"
CROSS_VIEW = ROOT / "prototype/cross-view/results.json"
FIRST_PROBE = ROOT / "validation/spin-observability/T11-handle-periodicity-first.json"
OUTPUT = ROOT / "validation/spin-observability/T11-handle-polarity-pilot.json"
FIGURE = ROOT / "validation/spin-observability/T11-handle-polarity-pilot.png"
TEMPLATE_LEFT_S = (2307.0, 2307.1, 2307.2)
TEMPLATE_RIGHT_S = (2308.6, 2308.7, 2308.8, 2308.9, 2309.0)
TOP_HANDLE_REGION = np.s_[18:35, :]


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def polarity(mask, left, right):
    patch = mask[TOP_HANDLE_REGION]
    left_mse = float(np.mean((patch - left[TOP_HANDLE_REGION]) ** 2))
    right_mse = float(np.mean((patch - right[TOP_HANDLE_REGION]) ** 2))
    return round(right_mse - left_mse, 5)


def summarize(rows, start, end):
    selected = [row["polarity"] for row in rows if start <= row["time_s"] <= end]
    if not selected:
        raise ValueError("Empty phase-control interval")
    return {
        "interval_s": [start, end],
        "count": len(selected),
        "mean_polarity": round(float(np.mean(selected)), 5),
        "positive_count": sum(value > 0 for value in selected),
        "negative_count": sum(value < 0 for value in selected),
    }


def main():
    if OUTPUT.exists() or FIGURE.exists():
        raise SystemExit("T11 handle-polarity pilot already exists")
    metadata = json.loads(SOURCE_META.read_text())
    first = json.loads(FIRST_PROBE.read_text())
    if digest(VIDEO) != first["source_video_sha256"] or (
        digest(CROSS_VIEW) != first["cross_view_results_sha256"]
    ):
        raise ValueError("First pilot source or track differs")
    crossview = json.loads(CROSS_VIEW.read_text())
    throw = next(row for row in crossview["throws"] if row["id"] == "T11")
    moving_times = np.round(np.arange(2307.0, 2312.51, 0.1), 3)
    settled_times = np.round(np.arange(2319.5, 2323.01, 0.1), 3)
    cap = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    if not cap.isOpened():
        raise RuntimeError("Cannot open T11 source")
    try:
        moving, moving_retained = mask_series(
            cap, throw, moving_times, metadata["source_interval_s"][0]
        )
        settled, settled_retained = mask_series(
            cap, throw, settled_times, metadata["source_interval_s"][0], settled=True
        )
    finally:
        cap.release()
    if len(moving_retained) != len(moving_times) or len(settled_retained) != len(settled_times):
        raise RuntimeError("Some handle masks were unavailable")
    by_time = {time_s: index for index, time_s in enumerate(moving_retained)}
    left = np.mean(moving[[by_time[t] for t in TEMPLATE_LEFT_S]], axis=0)
    right = np.mean(moving[[by_time[t] for t in TEMPLATE_RIGHT_S]], axis=0)
    moving_rows = [
        {"time_s": t, "polarity": polarity(mask, left, right)}
        for t, mask in zip(moving_retained, moving)
    ]
    settled_rows = [
        {"time_s": t, "polarity": polarity(mask, left, right)}
        for t, mask in zip(settled_retained, settled)
    ]
    intervals = {
        "initial_left": summarize(moving_rows, 2307.0, 2307.4),
        "opposite_right": summarize(moving_rows, 2308.5, 2309.3),
        "later_left": summarize(moving_rows, 2311.0, 2311.5),
        "settled_control": summarize(settled_rows, 2319.5, 2323.0),
    }
    if not (
        intervals["initial_left"]["mean_polarity"] > 0
        and intervals["opposite_right"]["mean_polarity"] < 0
        and intervals["later_left"]["mean_polarity"] > 0
    ):
        raise RuntimeError("Expected visible left/right/left pattern was not measured")
    fig, axes = plt.subplots(
        2, 1, figsize=(10, 5), sharey=True, gridspec_kw={"height_ratios": [2, 1]}
    )
    for ax, rows, title in (
        (axes[0], moving_rows, "Moving stone: receiving camera"),
        (axes[1], settled_rows, "Settled control"),
    ):
        ax.plot(
            [row["time_s"] for row in rows],
            [row["polarity"] for row in rows],
            marker=".",
            linewidth=1.5,
        )
        ax.axhline(0, color="black", linewidth=0.8)
        ax.set_title(title)
        ax.set_ylabel("Left (+) / right (−)\nmask similarity")
        ax.grid(alpha=0.25)
    axes[1].set_xlabel("Source video time (s)")
    fig.suptitle("T11 handle silhouette polarity — image cue, not revolution count")
    fig.tight_layout()
    fig.savefig(FIGURE, dpi=160)
    plt.close(fig)
    result = {
        "status": "exploratory_visible_left_right_left_handle_cycle_not_turn_count",
        "source_video_sha256": digest(VIDEO),
        "source_metadata_sha256": digest(SOURCE_META),
        "cross_view_results_sha256": digest(CROSS_VIEW),
        "first_periodicity_probe_sha256": digest(FIRST_PROBE),
        "mask_extraction_code_sha256": digest(
            ROOT / "prototype/scripts/probe_t11_handle_periodicity.py"
        ),
        "runner_sha256": digest(Path(__file__)),
        "figure_sha256": digest(FIGURE),
        "sample_rate_hz": 10,
        "template_left_times_s": TEMPLATE_LEFT_S,
        "template_right_times_s": TEMPLATE_RIGHT_S,
        "comparison_mask_rows": [18, 35],
        "interpretation": "Positive scores resemble the first left-facing template; negative scores resemble the right-facing template.",
        "interval_summaries": intervals,
        "moving_rows": moving_rows,
        "settled_control_rows": settled_rows,
        "limitations": [
            "The templates and intervals were selected after visually inspecting this exposed T11 clip.",
            "The signal classifies two side-view silhouettes; it is not a calibrated 0–360 degree angular phase.",
            "Viewpoint and compression can alter silhouettes; the settled control has a different pose.",
            "The observed cycle does not establish a full-throw revolution count or an error bound through camera cuts.",
        ],
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print({name: row["mean_polarity"] for name, row in intervals.items()})


if __name__ == "__main__":
    main()
