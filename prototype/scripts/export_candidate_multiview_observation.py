"""Export source-hashed candidate camera spans and explicit unobserved seams."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from candidate_multiview_observation import build_observation_windows


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sequence", type=Path, required=True)
    parser.add_argument("--left-tracks", type=Path, required=True)
    parser.add_argument("--right-proposals", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    inputs = {key: path for key, path in (
        ("sequence", args.sequence), ("left_tracks", args.left_tracks),
        ("right_proposals", args.right_proposals))}
    data = {key: json.loads(path.read_text()) for key, path in inputs.items()}
    output = build_observation_windows(data["sequence"], data["left_tracks"],
                                       data["right_proposals"])
    output["input_sha256"] = {key: digest(path) for key, path in inputs.items()}
    output["model_code_sha256"] = digest(ROOT / "prototype/candidate_multiview_observation.py")
    output["runner_sha256"] = digest(Path(__file__))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"candidates": output["candidate_count"],
                      "two_view": output["two_view_candidate_count"],
                      "median_seam_s": output["median_unobserved_camera_seam_s"]}))


if __name__ == "__main__":
    main()
