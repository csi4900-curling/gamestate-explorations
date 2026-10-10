"""Measure chance camera-aware links under time and colour negative controls."""

import argparse
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from camera_aware_right_fusion import fuse, right_entries


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def link_count(right, left):
    return sum(row["fusion_status"] == "cross_view_time_colour_corrob"
               for row in fuse(right, left, left))


def build_audit(right_path, left_path, fusion_path):
    right = json.loads(right_path.read_text())
    left = json.loads(left_path.read_text())
    recorded = json.loads(fusion_path.read_text())
    if (right["source_sha256"] != left["source_sha256"]
            or right["source_sha256"] != recorded["source_sha256"]):
        raise ValueError("Source fingerprints differ")
    if recorded["right_sha256"] != digest(right_path):
        raise ValueError("Recorded fusion does not use this right proposal file")
    if recorded["left_sha256"] != digest(left_path):
        raise ValueError("Recorded fusion does not use this left timeline")
    if recorded["fusion_code_sha256"] != digest(ROOT / "prototype/camera_aware_right_fusion.py"):
        raise ValueError("Fusion implementation changed since recorded output")
    observed_count = link_count(right, left)
    if observed_count != recorded["fusion_status_counts"].get("cross_view_time_colour_corrob", 0):
        raise ValueError("Cannot reproduce observed link count")

    entries = right_entries(right)
    start_s, end_s = right["source_interval_s"]
    duration_s = end_s - start_s
    if duration_s <= 60 or not entries:
        raise ValueError("Expected a nonempty full-match source interval")
    if any(not start_s <= entry["entry_crossing"]["time_s"] < end_s
           for entry in entries):
        raise ValueError("Right entry outside source interval")
    # Offset the complete sequence together, keeping inter-entry spacing and
    # colour order. Omit shifts near zero and the wrap boundary.
    shifts_s = list(range(30, int(duration_s) - 25, 30))
    time_shift_counts = []
    for delta_s in shifts_s:
        shifted = deepcopy(right)
        for entry in right_entries(shifted):
            t = entry["entry_crossing"]["time_s"]
            entry["entry_crossing"]["time_s"] = start_s + (t - start_s + delta_s) % duration_s
        time_shift_counts.append(link_count(shifted, left))

    swapped = deepcopy(right)
    for entry in right_entries(swapped):
        colour = entry["colour_claim"]
        if colour not in ("red", "yellow"):
            raise ValueError(f"Cannot swap colour {colour}")
        entry["colour_claim"] = "yellow" if colour == "red" else "red"
    swapped_count = link_count(swapped, left)
    return {
        "status": "development_negative_control_for_conditional_cross_view_links_not_event_accuracy",
        "source_sha256": right["source_sha256"],
        "right_sha256": digest(right_path),
        "left_sha256": digest(left_path),
        "observed_fusion_sha256": digest(fusion_path),
        "fusion_code_sha256": digest(ROOT / "prototype/camera_aware_right_fusion.py"),
        "runner_sha256": digest(Path(__file__)),
        "right_entry_count": len(entries),
        "observed_conditional_link_count": observed_count,
        "time_shift_control": {
            "shift_step_s": 30,
            "shift_offsets_s": shifts_s,
            "conditional_link_counts": time_shift_counts,
            "control_count": len(shifts_s),
            "minimum": min(time_shift_counts),
            "median": sorted(time_shift_counts)[len(time_shift_counts) // 2],
            "maximum": max(time_shift_counts),
            "controls_at_or_above_observed": sum(n >= observed_count for n in time_shift_counts),
        },
        "swapped_colour_control_conditional_link_count": swapped_count,
        "limitations": [
            "These deterministic negative controls reuse an exposed development match; they are not a held-out accuracy test.",
            "The time-shift control changes only entry timestamps for matching, not source pixels or the detected track itself.",
            "Original events and control offsets are dependent, so controls-at-or-above is not a calibrated p-value.",
            "Temporal and colour specificity do not establish physical stone identity, throw precision, recall, or F1.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("right", "left", "fusion", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    output = build_audit(args.right, args.left, args.fusion)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({
        "observed": output["observed_conditional_link_count"],
        "shift_control_max": output["time_shift_control"]["maximum"],
        "swapped_colour": output["swapped_colour_control_conditional_link_count"],
    }))


if __name__ == "__main__":
    main()
