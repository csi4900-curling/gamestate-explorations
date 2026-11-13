"""Score temporal isolation of frozen full-source possible-edit proposals."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from scene_cuts import scene_cut_evidence
from temporal_edit_isolation import edit_isolation


def digest(path):
    h = sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve the first temporal scan")
    plan = json.loads(args.plan.read_text())
    video = ROOT / plan["video_relative_path"]
    proposals_path = ROOT / plan["possible_edits_relative_path"]
    proposal_plan_path = ROOT / plan["possible_scan_plan_relative_path"]
    hashes = {
        "video": digest(video),
        "possible_scan_plan": digest(proposal_plan_path),
        "scene_code": digest(ROOT / "prototype/scene_cuts.py"),
        "isolation_code": digest(ROOT / "prototype/temporal_edit_isolation.py"),
        "runner": digest(__file__),
    }
    if hashes != plan["sha256"]:
        raise ValueError("Frozen temporal-isolation plan changed")
    proposals = json.loads(proposals_path.read_text())
    if (
        proposals["source_sha256"] != hashes["video"]
        or proposals["plan_sha256"] != hashes["possible_scan_plan"]
    ):
        raise ValueError("Possible-edit artifact does not match planned source")
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    if hashes["video"] == reserved["source_sha256"]:
        raise ValueError("Reserved independent source selected")
    capture = cv2.VideoCapture(str(video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    fps = capture.get(cv2.CAP_PROP_FPS)
    spacing = 1 / proposals["sample_rate_hz"]
    rows = []
    for item in proposals["possible_edits_outside_hard_cuts"]:
        time_s = item["time_s"]
        frames = []
        for offset in (-2 * spacing, -spacing, 0, spacing):
            instant = time_s + offset
            if not proposals["sample_rate_hz"] or instant < 0:
                raise ValueError(f"Cannot sample temporal context: {time_s}")
            capture.set(cv2.CAP_PROP_POS_FRAMES, round(instant * fps))
            ok, frame = capture.read()
            if not ok:
                raise RuntimeError(f"Frame decode failed at {instant}")
            frames.append(frame)
        metrics = [scene_cut_evidence(a, b) for a, b in zip(frames, frames[1:])]
        if (
            metrics[1]["gray_change"] != item["gray_change"]
            or metrics[1]["hist_distance"] != item["hist_distance"]
        ):
            raise ValueError(f"Central pair mismatch at {time_s}")
        isolation = edit_isolation(
            *metrics,
            min_gray_ratio=plan["minimum_gray_isolation_ratio"],
            min_hist_ratio=plan["minimum_hist_isolation_ratio"],
        )
        rows.append(
            {
                "time_s": time_s,
                "shot_id": item["shot_id"],
                "adjacent_pair_metrics": metrics,
                **isolation,
            }
        )
    capture.release()
    counts = Counter(
        "isolated_spike" if row["isolated_spike"] else "nonisolated_change" for row in rows
    )
    output = {
        "status": "first_source_only_temporal_isolation_of_possible_edits_not_verified_cut_score",
        "source_id": plan["source_id"],
        "source_sha256": hashes["video"],
        "plan_sha256": digest(args.plan),
        "possible_edits_sha256": digest(proposals_path),
        "sha256": hashes,
        "pair_spacing_s": spacing,
        "counts": dict(counts),
        "rows": rows,
        "limitations": [
            "Thresholds were selected after inspecting China and Swiss development examples.",
            "An isolated spike is a source-only edit cue, not a verified camera cut.",
            "Gradual edits and cuts accompanied by foreground motion can fail isolation.",
            "No event labels, counter colours or official shots enter the calculation.",
        ],
    }
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print(
        {
            "source": plan["source_id"],
            "proposals": len(rows),
            "isolated": counts["isolated_spike"],
            "nonisolated": counts["nonisolated_change"],
        }
    )


if __name__ == "__main__":
    main()
