"""Export end-three cross-view observations with explicit physics limits."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256  # noqa: E402
from cross_view_observation_handoff import build_observation_handoff  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cross-view", type=Path, required=True)
    parser.add_argument("--far-paths", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Observation handoff already exists")
    cross_view = json.loads(args.cross_view.read_text())
    far_paths = json.loads(args.far_paths.read_text())
    if far_paths["source_clip_sha256"] != file_sha256(
            ROOT / "prototype/throw-analysis/end3.mp4"):
        parser.error("Far paths do not match end-three source")
    handoff = build_observation_handoff(cross_view["throws"], far_paths["rows"])
    handoff.update({
        "status": "development_end3_observed_cross_view_paths_not_physics_simulation",
        "source_video_sha256": far_paths["source_clip_sha256"],
        "cross_view_sha256": file_sha256(args.cross_view),
        "far_paths_sha256": file_sha256(args.far_paths),
        "handoff_code_sha256": file_sha256(
            ROOT / "prototype/cross_view_observation_handoff.py"),
        "runner_sha256": file_sha256(__file__),
    })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(handoff, indent=2) + "\n")
    print({"throws": handoff["throw_count"],
           "far_paths": handoff["far_path_selected_count"],
           "ambiguous": handoff["ambiguous_or_unresolved_count"]})


if __name__ == "__main__":
    main()
