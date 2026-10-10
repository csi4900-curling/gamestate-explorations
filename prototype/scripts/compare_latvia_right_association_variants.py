"""Compare full-match right proposal inventories by time, colour and direction."""

from hashlib import sha256
import json
from pathlib import Path

import numpy as np
from scipy.optimize import linear_sum_assignment


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark/canada-latvia-2024"
VIDEO = BASE / "source-360p.mp4"
SCANS = {
    "one_second_greedy": BASE / "full-right-area-first-transfer.json",
    "two_second_greedy": BASE / "full-right-area-gap2-development.json",
    "two_second_global": BASE / "full-right-global-area-development.json",
}
OUT = BASE / "full-right-association-variant-comparison-development.json"
WINDOW_S = 8


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def proposal_time(row):
    return row["passage"]["time_s"]


def compare(left, right):
    if not left or not right:
        raise ValueError("Cannot compare empty proposal sets")
    n_left, n_right = len(left), len(right)
    costs = np.full((n_left, n_right + n_left), 1e6, dtype=float)
    for index, first in enumerate(left):
        costs[index, n_right + index] = 1000
        for other, second in enumerate(right):
            if (
                first["colour_claim"] != second["colour_claim"]
                or first["direction"] != second["direction"]
            ):
                continue
            delta = abs(proposal_time(first) - proposal_time(second))
            if delta <= WINDOW_S:
                costs[index, other] = delta + index * 1e-8 + other * 1e-10
    row_indices, col_indices = linear_sum_assignment(costs)
    pairs = []
    paired_left, paired_right = set(), set()
    for index, other in zip(row_indices, col_indices):
        if other >= n_right or costs[index, other] >= 1000:
            continue
        first, second = left[index], right[other]
        pairs.append(
            {
                "left_raw_track_id": first["raw_track_id"],
                "right_raw_track_id": second["raw_track_id"],
                "left_time_s": proposal_time(first),
                "right_time_s": proposal_time(second),
                "absolute_time_delta_s": abs(proposal_time(first) - proposal_time(second)),
                "colour_claim": first["colour_claim"],
                "direction": first["direction"],
            }
        )
        paired_left.add(index)
        paired_right.add(other)
    pairs.sort(key=lambda row: row["left_time_s"])
    return {
        "left_proposal_count": n_left,
        "right_proposal_count": n_right,
        "temporal_pair_count": len(pairs),
        "left_unpaired": [
            {
                "raw_track_id": row["raw_track_id"],
                "time_s": proposal_time(row),
                "colour_claim": row["colour_claim"],
                "direction": row["direction"],
            }
            for index, row in enumerate(left)
            if index not in paired_left
        ],
        "right_unpaired": [
            {
                "raw_track_id": row["raw_track_id"],
                "time_s": proposal_time(row),
                "colour_claim": row["colour_claim"],
                "direction": row["direction"],
            }
            for index, row in enumerate(right)
            if index not in paired_right
        ],
        "pairs": pairs,
    }


def main():
    if OUT.exists():
        raise ValueError("Variant comparison already exists")
    scans = {name: json.loads(path.read_text()) for name, path in SCANS.items()}
    source_hash = digest(VIDEO)
    if any(
        scan["source_sha256"] != source_hash or scan["source_interval_s"] != [0, 7058]
        for scan in scans.values()
    ):
        raise ValueError("Variant scans use different source bytes or intervals")
    proposals = {name: scan["directional_review_proposals"] for name, scan in scans.items()}
    for name, scan in scans.items():
        if len(proposals[name]) != scan["directional_proposal_count"] or len(
            {row["raw_track_id"] for row in proposals[name]}
        ) != len(proposals[name]):
            raise ValueError(f"Duplicate or missing right proposals in {name}")
    result = {
        "status": "development_temporal_proposal_inventory_comparison_not_throw_truth",
        "source_video_sha256": source_hash,
        "scan_sha256": {name: digest(path) for name, path in SCANS.items()},
        "runner_sha256": digest(Path(__file__)),
        "comparison_rule": "global one-to-one maximum-cardinality match, then minimum passage-time difference, with identical colour/direction and <=8 s difference",
        "window_s": WINDOW_S,
        "scan_counts": {
            name: {
                "raw_tracks": scan["raw_track_count"],
                "review_proposals": scan["directional_proposal_count"],
            }
            for name, scan in scans.items()
        },
        "comparisons": {
            "one_vs_greedy_two": compare(
                proposals["one_second_greedy"], proposals["two_second_greedy"]
            ),
            "one_vs_global_two": compare(
                proposals["one_second_greedy"], proposals["two_second_global"]
            ),
            "greedy_two_vs_global_two": compare(
                proposals["two_second_greedy"], proposals["two_second_global"]
            ),
        },
        "limitations": [
            "A temporal pair is not proof of same-stone identity or a physical delivery.",
            "Track IDs are local to each scan; only source times, colour and image direction enter matching.",
            "An unmatched proposal can reflect timestamp shifts, merged/split paths, people, or a source-visible stone; source review is required.",
            "The two-second variants were evaluated after Latvia R008 was known, so this is development comparison, not a held-out event score.",
        ],
    }
    OUT.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                key: {
                    "paired": value["temporal_pair_count"],
                    "left_unpaired": len(value["left_unpaired"]),
                    "right_unpaired": len(value["right_unpaired"]),
                }
                for key, value in result["comparisons"].items()
            }
        )
    )


if __name__ == "__main__":
    main()
