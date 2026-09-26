"""Describe every difference after a reproduction; never relax its pass threshold.

This supplements reproduce.py's strict comparison with coordinate magnitudes and
discrete changes. It does not certify physical accuracy or declare differences acceptable.
"""

from pathlib import Path
import argparse
import json
import math

from reproduce import ROOT, OUTPUTS, METADATA_KEYS, load

POSITION_KEYS = {
    "position_m",
    "position_local_m",
    "ground_position_m",
    "world_m",
    "predicted_metric_m",
    "diagram_metric_m",
    "corrected_position_m",
    "uncorrected_position_m",
    "ice_plane_projection_m",
}
PIXEL_KEYS = {"pixel", "pixel_center", "seed_pixel", "reference_pixel"}


def describe(original, fresh):
    result = {
        "discrete_changes": 0,
        "discrete_examples": [],
        "changed_numbers": 0,
        "max_position_shift_m": 0.0,
        "max_pixel_shift_px": 0.0,
        "max_scalar_difference": 0.0,
        "max_scalar_path": None,
    }

    def discrete(path, a, b):
        result["discrete_changes"] += 1
        if len(result["discrete_examples"]) < 12:
            result["discrete_examples"].append(
                {"path": path, "before": str(a)[:160], "after": str(b)[:160]}
            )

    def walk(a, b, path="$", key=""):
        if isinstance(a, dict) and isinstance(b, dict):
            ka, kb = set(a) - METADATA_KEYS, set(b) - METADATA_KEYS
            if ka != kb:
                discrete(path + ".keys", sorted(ka), sorted(kb))
            for k in sorted(ka & kb):
                walk(a[k], b[k], path + "." + k, k)
        elif isinstance(a, list) and isinstance(b, list):
            if len(a) != len(b):
                discrete(path + ".length", len(a), len(b))
                return
            if len(a) == 2 and all(type(v) in (int, float) for v in a + b):
                target = (
                    "max_position_shift_m"
                    if key in POSITION_KEYS
                    else "max_pixel_shift_px"
                    if key in PIXEL_KEYS
                    else None
                )
                if target:
                    result[target] = max(result[target], math.dist(a, b))
            for i, (x, y) in enumerate(zip(a, b)):
                walk(x, y, f"{path}[{i}]", key)
        elif type(a) in (int, float) and type(b) in (int, float):
            if a != b:
                result["changed_numbers"] += 1
                difference = abs(a - b)
                if difference > result["max_scalar_difference"]:
                    result["max_scalar_difference"] = difference
                    result["max_scalar_path"] = path
                if type(a) is int and type(b) is int:
                    discrete(path, a, b)
        elif a != b:
            discrete(path, a, b)

    walk(original, fresh)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = []
    for relative in OUTPUTS:
        a, b = ROOT / relative, args.workspace / relative
        if not a.exists():
            continue
        row = {"file": relative}
        if not b.exists():
            row["error"] = "Fresh output missing"
        else:
            row.update(describe(load(a), load(b)))
        rows.append(row)
    report = {
        "scope": "Diagnostic only; strict tolerances in reproduce.py remain unchanged.",
        "ignored_metadata": sorted(METADATA_KEYS),
        "files": rows,
    }
    args.output.write_text(json.dumps(report, indent=2))
    print(args.output)


if __name__ == "__main__":
    main()
