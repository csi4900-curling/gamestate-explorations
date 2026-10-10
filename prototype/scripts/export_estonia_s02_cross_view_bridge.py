"""Reproducible Estonia S02 observation handoff for game-state consumers."""

from hashlib import sha256
import json
from pathlib import Path
import sys
from copy import deepcopy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cross_view_bridge_evidence import build_cross_view_bridge_evidence

BASE = ROOT / "validation/throw-event-benchmark/canada-estonia-2024"
INPUTS = {
    "episode": ROOT / "validation/throw-event-benchmark/layout-router/full-2024-coverage/yellow-bidirectional-motion-episodes-postscore.json",
    "edge": BASE / "yellow-s02-edge-timing-postreview.json",
    "left_bridge": BASE / "yellow-s02-left-entry-to-prior-path-postreview.json",
    "left_candidate": BASE / "left-bound-full-interval/s02-paired.json",
    "expanded_right": ROOT / "validation/throw-event-benchmark/layout-router/full-2024-coverage/yellow-full-right-panel-contour-transfer-postreview-v2.json",
}
OUTPUT = BASE / "yellow-s02-cross-view-observation-handoff-postreview-v2.json"


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    payloads = {key: json.loads(path.read_text()) for key, path in INPUTS.items()}
    episodes = [row for row in payloads["episode"]["rows"]
                if row["source"] == "estonia"]
    if len(episodes) != 1:
        raise ValueError("Expected one Estonia motion episode")
    source_path = BASE / "source-1080p-1650-2760.mp4"
    if digest(source_path) != payloads["edge"]["video_sha256"]:
        raise ValueError("Source video changed")
    right_rows = [row for row in payloads["expanded_right"]["rows"]
                  if row["source"] == "estonia"]
    if (len(right_rows) != 1 or
            payloads["expanded_right"]["source_sha256"]["estonia"] !=
            payloads["edge"]["video_sha256"] or
            payloads["expanded_right"]["episodes_sha256"] != digest(INPUTS["episode"]) or
            not right_rows[0]["last_linked_near_bottom_boundary"]):
        raise ValueError("Expanded right path does not match Estonia source and episode")
    episode = deepcopy(episodes[0])
    episode["continuation"] = right_rows[0]["path"]
    evidence = build_cross_view_bridge_evidence(
        episode, payloads["edge"], payloads["left_bridge"],
        payloads["left_candidate"])
    evidence["provenance"] = {
        "input_sha256": {key: digest(path) for key, path in INPUTS.items()},
        "builder_sha256": digest(ROOT / "prototype/cross_view_bridge_evidence.py"),
        "runner_sha256": digest(Path(__file__)),
    }
    OUTPUT.write_text(json.dumps(evidence, indent=2) + "\n")
    print(OUTPUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
