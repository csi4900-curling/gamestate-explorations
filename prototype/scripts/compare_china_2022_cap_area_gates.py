"""Diagnose resolution-scaled versus past-size cap gates on 2022 source."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from causal_cap_continuation import choose_next_cap  # noqa: E402

BASE = ROOT / "validation/official-shot-sequence"
SOURCE = BASE / "china-2022-cap-continuation-scale-transfer-development.json"
OUT = BASE / "china-2022-cap-area-gate-sensitivity-development.json"
SCALE = 3.0
GATES = {"scaled_czech_absolute_area": None,
         "past_cap_area_0p33_to_3": (1 / 3, 3),
         "past_cap_area_0p5_to_2": (0.5, 2),
         "past_cap_area_0p75_to_1p5": (0.75, 1.5),
         "no_area_limit_diagnostic": (0, float("inf"))}


def digest(path):
    h = sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def eligible_components(row, gate):
    raw = row["raw_colour_components"]
    if gate is None:
        return [c for c in raw if 20 / SCALE**2 <= c["area_px2"]
                <= 700 / SCALE**2]
    past_area = row["last_two_reconstructed_points_360"][-1][
        "cap_area_px2"]
    return [c for c in raw if gate[0] * past_area <= c["area_px2"]
            <= gate[1] * past_area]


def score(row, gate):
    points = row["last_two_reconstructed_points_360"]
    previous = [v * SCALE for v in points[-2]["pixel"]]
    current = [v * SCALE for v in points[-1]["pixel"]]
    ratio = 0.5 / (points[-1]["time_s"] - points[-2]["time_s"])
    components = [{**c, "centroid_px_1080": [round(v * SCALE, 3)
                                            for v in c["centroid_px_1080"]]}
                  for c in eligible_components(row, gate)]
    return choose_next_cap(current, previous, ratio, components)


def main():
    if OUT.exists():
        raise ValueError("2022 area-gate sensitivity already exists")
    source = json.loads(SOURCE.read_text())
    if source["selector_code_sha256"] != digest(ROOT /
                                               "prototype/causal_cap_continuation.py"):
        raise ValueError("Selector changed since source inventory")
    rows = []
    counts = {name: Counter() for name in GATES}
    reason_counts = Counter()
    for case in source["rows"]:
        if case["shot_boundary_abstention"]:
            continue
        statuses = {}
        for name, gate in GATES.items():
            decision = score(case, gate)
            statuses[name] = decision["status"]
            counts[name][decision["status"]] += 1
        absolute = eligible_components(case, None)
        if statuses["scaled_czech_absolute_area"] == "no_cap_inside_motion_gate":
            reason = ("no_raw_colour_component" if not case[
                "raw_colour_components"] else
                "all_components_excluded_by_absolute_area" if not absolute
                else "components_fail_motion_gate")
            reason_counts[reason] += 1
        else:
            reason = None
        rows.append({
            "episode_id": case["episode_id"],
            "camera_shot_id": case["camera_shot_id"],
            "colour": case["colour"],
            "last_cap_area_px2_360": case[
                "last_two_reconstructed_points_360"][-1]["cap_area_px2"],
            "next_frame_raw_component_areas_px2_360": [c["area_px2"]
                for c in case["raw_colour_components"]],
            "status_by_gate": statuses,
            "absolute_gate_failure_reason": reason,
            "physical_stone_identity_verified": False,
        })
    if len(rows) != source["source_catalog_track_count"] - source[
            "status_counts"]["camera_shot_boundary"]:
        raise ValueError("2022 in-shot track inventory differs")
    if dict(counts["scaled_czech_absolute_area"]) != {
            k: v for k, v in source["status_counts"].items()
            if k != "camera_shot_boundary"}:
        raise ValueError("Absolute-gate source statuses not reproduced")
    result = {
        "status": "postinspection_cap_area_gate_sensitivity_not_identity_accuracy",
        "source_video_sha256": source["source_video_sha256"],
        "input_sha256": {"one_step_scale_transfer": digest(SOURCE)},
        "runner_sha256": digest(Path(__file__)),
        "selector_code_sha256": source["selector_code_sha256"],
        "gate_definitions": {
            "scaled_czech_absolute_area": "20/9 to 700/9 source px²; Czech-developed absolute contour gate scaled by resolution area",
            "past_cap_area_0p33_to_3": "next contour area between 1/3 and 3 times last observed source cap area",
            "past_cap_area_0p5_to_2": "next contour area between 1/2 and 2 times last observed source cap area",
            "past_cap_area_0p75_to_1p5": "next contour area between 3/4 and 1.5 times last observed source cap area",
            "no_area_limit_diagnostic": "all raw colour contours in the search ROI",
        },
        "in_shot_track_count": len(rows),
        "status_counts_by_gate": {name: dict(count)
                                  for name, count in counts.items()},
        "absolute_gate_failure_reason_counts": dict(reason_counts),
        "rows": rows,
        "limitations": [
            "Relative-size gates were considered after inspecting the 2022 failure; these are in-sample diagnostic variants, not a frozen transfer result.",
            "A next-frame colour contour matching a past cap size and motion can still be a different stone, player, graphic or tracking splice.",
            "The comparison uses existing shot-scoped cap tracks, not independently labelled physical throws or complete game states.",
            "No variant should be promoted without source-pixel error review and independent cross-camera validation.",
        ],
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"in_shot": len(rows),
                      "counts": result["status_counts_by_gate"],
                      "absolute_failures": dict(reason_counts)}))


if __name__ == "__main__":
    main()
