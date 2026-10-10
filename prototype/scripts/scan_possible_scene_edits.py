"""Scan a full recording for possible edits missed by conservative hard cuts."""

import argparse
from bisect import bisect_right
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from scene_cuts import scene_cut_evidence


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
        parser.error("Output exists; preserve the first possible-edit scan")
    plan = json.loads(args.plan.read_text())
    video = ROOT / plan["video_relative_path"]
    hard_path = ROOT / plan["hard_cuts_relative_path"]
    expected = plan["sha256"]
    actual = {"video": digest(video), "hard_cuts": digest(hard_path),
              "scene_code": digest(ROOT / "prototype/scene_cuts.py"),
              "runner": digest(__file__)}
    if actual != expected:
        raise ValueError("Frozen possible-edit plan input changed")
    hard = json.loads(hard_path.read_text())
    if hard["source_sha256"] != actual["video"] or hard["source_interval_s"] != plan[
        "source_interval_s"
    ]:
        raise ValueError("Hard-cut artifact does not cover planned source")
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    if actual["video"] == reserved["source_sha256"]:
        raise ValueError("Reserved independent source selected")
    capture = cv2.VideoCapture(str(video), cv2.CAP_FFMPEG,
                               [cv2.CAP_PROP_N_THREADS, 1])
    fps = capture.get(cv2.CAP_PROP_FPS)
    step = round(fps / plan["sample_rate_hz"])
    if fps / step != hard["sample_rate_hz"]:
        raise ValueError("Sample rate differs from frozen hard-cut scan")
    start, end = plan["source_interval_s"]
    first, last = round(start * fps), round(end * fps)
    capture.set(cv2.CAP_PROP_POS_FRAMES, first)
    previous = None
    observed_hard = []
    possible = []
    sample_count = 0
    for index in range(first, last):
        if not capture.grab():
            raise RuntimeError(f"Decode failed at frame {index}")
        if (index - first) % step:
            continue
        ok, frame = capture.retrieve()
        if not ok:
            raise RuntimeError(f"Retrieve failed at frame {index}")
        time_s = round(index / fps, 3)
        if previous is not None:
            evidence = scene_cut_evidence(previous, frame)
            if evidence["hard_cut"]:
                observed_hard.append(time_s)
            if (evidence["gray_change"] >= plan["minimum_gray_change"] and
                    evidence["hist_distance"] >= plan["minimum_hist_distance"]):
                possible.append({"time_s": time_s, **evidence})
        previous = frame
        sample_count += 1
        if sample_count % 10000 == 0:
            print(f"scanned {sample_count} frames", flush=True)
    capture.release()
    hard_times = [row["time_s"] for row in hard["cuts"]]
    if observed_hard != hard_times or sample_count != hard["sample_count"]:
        raise ValueError("Full scan failed to reproduce existing hard cuts")
    novel = []
    for row in possible:
        time_s = row["time_s"]
        shot_index = bisect_right(hard_times, time_s)
        nearest = min((abs(time_s - hard_times[i])
                       for i in (shot_index - 1, shot_index)
                       if 0 <= i < len(hard_times)), default=float("inf"))
        if nearest > plan["hard_cut_exclusion_s"]:
            novel.append({**row, "shot_id": f"S{shot_index + 1:02d}",
                          "distance_to_nearest_hard_cut_s": round(nearest, 3)})
    shot_counts = Counter(row["shot_id"] for row in novel)
    output = {
        "status": "first_full_source_only_possible_edit_diagnostic_not_verified_cut_recall",
        "source_id": plan["source_id"],
        "source_sha256": actual["video"],
        "plan_sha256": digest(args.plan),
        "sha256": actual,
        "sample_rate_hz": fps / step,
        "sample_count": sample_count,
        "reproduced_hard_cut_count": len(observed_hard),
        "possible_edit_count": len(possible),
        "possible_edits_outside_hard_cuts_count": len(novel),
        "affected_existing_camera_shot_count": len(shot_counts),
        "possible_edits_outside_hard_cuts": novel,
        "shot_counts": dict(sorted(shot_counts.items())),
        "limitations": [
            "Thresholds came from selected development examples; candidates are not verified edits.",
            "Frame changes can also come from pans, zooms, graphics, dissolves or motion blur.",
            "The conservative hard-cut output and event ledger are unchanged.",
            "A camera edit is not a physical throw event or a stone identity link.",
        ],
    }
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print({"source": plan["source_id"], "hard": len(observed_hard),
           "possible": len(possible), "novel": len(novel),
           "affected_shots": len(shot_counts)})


if __name__ == "__main__":
    main()
