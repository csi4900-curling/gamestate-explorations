"""Freeze likely window-truncated track pairs without merging them."""

from hashlib import sha256
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from prototype.motion_episode_near_duplicates import find_near_duplicate_pairs


SOURCE = ROOT / "validation/official-shot-sequence/norway-motion-episode-registry-first.json"
OUTPUT = ROOT / "validation/official-shot-sequence/norway-motion-episode-near-duplicates-first.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first near-duplicate audit")
    source = json.loads(SOURCE.read_text())
    if len(source["episodes"]) != source["episode_count"]:
        raise SystemExit("Episode count disagrees with registry")
    pairs = find_near_duplicate_pairs(source["episodes"])
    result = {
        "status": "source_only_possible_window_truncation_pairs_not_merged",
        "episode_registry_sha256": digest(SOURCE),
        "audit_code_sha256": digest(ROOT / "prototype/motion_episode_near_duplicates.py"),
        "runner_sha256": digest(Path(__file__)),
        "selection_rule": {
            "same_colour": True,
            "different_candidate_sets": True,
            "positive_time_overlap": True,
            "maximum_onset_difference_s": 1.0,
            "maximum_end_difference_s": 5.0,
            "maximum_span_difference_px": 0.01,
            "maximum_first_and_last_pixel_distance_px": 2.0,
        },
        "input_exact_episode_count": source["episode_count"],
        "possible_duplicate_pair_count": len(pairs),
        "pairs": pairs,
        "limitations": [
            "Rule was selected after examining this Norway transfer and is a development diagnostic, not independent validation.",
            "Matched endpoints and timing strongly suggest window truncation but do not prove physical identity.",
            "Other split records may be missed, especially across camera cuts or shifted track origins.",
            "Pairs are not merged and no candidate is assigned a verified throw.",
        ],
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print(
        {
            "possible_duplicate_pair_count": len(pairs),
            "episode_pairs": [row["episode_ids"] for row in pairs],
        }
    )


if __name__ == "__main__":
    main()
