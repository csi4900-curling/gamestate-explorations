"""Export a traceable, bounded-time review queue across right-view variants."""

from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from right_variant_review_queue import build_review_queue

BASE = ROOT / "validation/throw-event-benchmark/canada-latvia-2024"
FILES = {
    "one_second_greedy": BASE / "full-right-area-first-transfer.json",
    "two_second_greedy": BASE / "full-right-area-gap2-development.json",
    "two_second_global": BASE / "full-right-global-area-development.json",
    "two_second_global_later": BASE / "full-right-global-multi-episode-development.json",
}
WITNESSES = BASE / "full-right-source-stone-witness-coverage-development.json"
OUTPUT = BASE / "full-right-variant-review-queue-development.json"
WINDOW_S = 8.0


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def main():
    scans = {name: json.loads(path.read_text()) for name, path in FILES.items()}
    source_hash = digest(BASE / "source-360p.mp4")
    if any(scan["source_sha256"] != source_hash or
           scan["source_interval_s"] != [0, 7058]
           for scan in scans.values()):
        raise ValueError("Variant source bytes or intervals disagree")
    if scans["two_second_global_later"]["global_scan_sha256"] != digest(
            FILES["two_second_global"]):
        raise ValueError("Later episodes are not derived from the global scan")
    variants = {name: scans[name]["directional_review_proposals"] for name in (
        "one_second_greedy", "two_second_greedy", "two_second_global")}
    for name, rows in variants.items():
        if len(rows) != scans[name]["directional_proposal_count"]:
            raise ValueError(f"Proposal count mismatch: {name}")
    variants["two_second_global_later"] = scans[
        "two_second_global_later"]["later_review_proposals"]
    if len(variants["two_second_global_later"]) != scans[
            "two_second_global_later"]["later_quiet_separated_proposal_count"]:
        raise ValueError("Later episode count mismatch")
    proposals, groups = build_review_queue(variants, window_s=WINDOW_S)

    witness_file = json.loads(WITNESSES.read_text())
    if witness_file["source_video_sha256"] != source_hash:
        raise ValueError("Witness source differs")
    witnesses = []
    for witness in witness_file["witnesses"]:
        matches = [row["proposal_id"] for row in proposals
                   if row["colour_claim"] == witness["colour_claim"]
                   and row["direction"] == witness["direction"]
                   and abs(row["time_s"] - witness["source_time_s"]) <= WINDOW_S]
        witnesses.append({"witness_id": witness["witness_id"],
                          "temporally_matching_proposal_ids": matches})
    result = {
        "status": "development_review_queue_not_verified_physical_throws",
        "source_video_sha256": source_hash,
        "source_interval_s": [0, 7058],
        "input_sha256": {name: digest(path) for name, path in FILES.items()},
        "witness_sha256": digest(WITNESSES),
        "queue_code_sha256": digest(ROOT / "prototype/right_variant_review_queue.py"),
        "runner_sha256": digest(Path(__file__)),
        "grouping_window_s": WINDOW_S,
        "grouping_rule": "Same colour and image direction; every group spans at most 8 s. Groups only organize source review and do not merge physical events.",
        "variant_proposal_counts": {name: len(rows) for name, rows in variants.items()},
        "proposal_count": len(proposals),
        "review_group_count": len(groups),
        "multi_proposal_review_group_count": sum(len(group["proposal_ids"]) > 1
                                                  for group in groups),
        "source_visible_witness_count": len(witnesses),
        "source_visible_witnesses_with_temporal_proposal": sum(
            bool(row["temporally_matching_proposal_ids"]) for row in witnesses),
        "witnesses": witnesses,
        "proposals": proposals,
        "review_groups": groups,
        "limitations": [
            "A review group is not a physical throw, event deduplication, or a persistent stone identity.",
            "Time/colour/direction agreement is only a source-review shortcut; people and equipment can match.",
            "The 19 witnesses are same-agent source-visible paths found after proposal review, not exhaustive blind ground truth or physical-throw recall.",
            "The variants were developed on this match. Independent full-match labels are still needed for precision, recall and F1.",
            "No release/settle time, complete board, metric trajectory, spin count, or simulation-ready state is inferred.",
        ],
    }
    OUTPUT.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"proposals": len(proposals), "review_groups": len(groups),
                      "witness_coverage": result[
                          "source_visible_witnesses_with_temporal_proposal"]}))


if __name__ == "__main__":
    main()
