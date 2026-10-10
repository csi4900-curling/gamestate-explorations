"""Audit one full-match candidate ledger against official shot order.

The official shot sequence is used only for post-transfer diagnosis, not for
video-only event inference or an independent event-F1 estimate.
"""

import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.official_candidate_sequence import align_official_sequence


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--official", required=True, type=Path)
    parser.add_argument("--first-transfer", required=True, type=Path)
    parser.add_argument("--candidates", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve first sequence diagnostic")
    official = json.loads(args.official.read_text())
    transfer = json.loads(args.first_transfer.read_text())
    ledger = json.loads(args.candidates.read_text())
    source_hash = official["source_video_sha256"]
    if ledger["source_sha256"] != source_hash or transfer["source_video_sha256"] != source_hash:
        parser.error("Input sources differ")
    if transfer["official_ledger_sha256"] != digest(args.official):
        parser.error("Transfer uses a different official ledger")
    if transfer["input_sha256"]["candidate_ledger"] != digest(args.candidates):
        parser.error("Transfer uses a different candidate ledger")
    candidates = ledger["events"]
    if len(candidates) != ledger["candidate_count"]:
        parser.error("Candidate ledger count mismatch")
    by_counter = {row["counter_id"]: row for row in candidates if row["counter_id"]}
    if len(by_counter) != sum(bool(row["counter_id"]) for row in candidates):
        parser.error("Several candidates link to one counter")
    shot_to_end = {
        shot["official_shot_id"]: end["end"] for end in official["ends"] for shot in end["shots"]
    }
    fixed_by_end = defaultdict(dict)
    anchor_times = defaultdict(list)
    for row in transfer["counter_alignment_rows"]:
        if row["status"] != "unique_colour_concordant":
            continue
        candidate = by_counter.get(row["counter_id"])
        if candidate is None:
            continue
        shot_id = row["official_shot_id"]
        end = shot_to_end[shot_id]
        fixed_by_end[end][candidate["candidate_id"]] = shot_id
        anchor_times[end].append(candidate["observation_anchor_s"])
    ends = [end["end"] for end in official["ends"]]
    if set(anchor_times) != set(ends):
        parser.error("Every end needs a clean candidate anchor")
    boundaries = [
        (max(anchor_times[left]) + min(anchor_times[right])) / 2
        for left, right in zip(ends, ends[1:])
    ]
    if any(right <= left for left, right in zip(boundaries, boundaries[1:])):
        parser.error("Inferred end partitions overlap or reverse")
    grouped = defaultdict(list)
    for candidate in candidates:
        end = 1 + sum(candidate["observation_anchor_s"] > boundary for boundary in boundaries)
        grouped[end].append(candidate)
    end_rows = []
    for end in official["ends"]:
        number = end["end"]
        ordered = sorted(
            grouped[number], key=lambda row: (row["observation_anchor_s"], row["candidate_id"])
        )
        if not set(fixed_by_end[number]).issubset({row["candidate_id"] for row in ordered}):
            parser.error("Fixed counter link fell in a different inferred end")
        result = align_official_sequence(
            ordered, end["shots"], official["team_handle_colours"], fixed_by_end[number]
        )
        end_rows.append(
            {
                "end": number,
                "candidate_count": len(ordered),
                "official_shot_count": len(end["shots"]),
                "clean_fixed_link_count": len(fixed_by_end[number]),
                "minimum_edit_cost": result["minimum_cost"],
                "equally_optimal_alignment_count": result["optimal_path_count"],
                "candidate_status_counts": dict(
                    Counter(row["status"] for row in result["candidate_rows"])
                ),
                "official_status_counts": dict(
                    Counter(row["status"] for row in result["official_rows"])
                ),
                "candidate_rows": result["candidate_rows"],
                "official_rows": result["official_rows"],
            }
        )
    output = {
        "status": "post_transfer_official_sequence_diagnostic_not_video_event_f1",
        "source_sha256": source_hash,
        "official_sha256": digest(args.official),
        "first_transfer_sha256": digest(args.first_transfer),
        "candidate_ledger_sha256": digest(args.candidates),
        "sequence_code_sha256": digest(ROOT / "prototype/official_candidate_sequence.py"),
        "runner_sha256": digest(Path(__file__)),
        "end_partition_midpoints_s": boundaries,
        "candidate_count": len(candidates),
        "official_shot_count": official["official_shot_count"],
        "clean_fixed_link_count": sum(len(rows) for rows in fixed_by_end.values()),
        "candidate_status_counts": dict(
            Counter(
                status
                for end in end_rows
                for row in end["candidate_rows"]
                for status in [row["status"]]
            )
        ),
        "official_status_counts": dict(
            Counter(
                status
                for end in end_rows
                for row in end["official_rows"]
                for status in [row["status"]]
            )
        ),
        "ends": end_rows,
        "limitations": [
            "Official shot order and colour are used only for diagnosis; this is not a deployable detector.",
            "Unique optimal alignment depends on the stated edit costs and does not prove physical identity.",
            "Skipped candidates are review priorities, not verified false positives.",
            "End partitions are midpoint diagnostics, not source-reviewed physical boundaries.",
            "Official shot pages have no video release timestamps, so precision and recall remain unmeasured.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print(output["candidate_status_counts"])
    print(output["official_status_counts"])


if __name__ == "__main__":
    main()
