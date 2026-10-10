"""Score frozen candidate windows against source-only development review.

This is a diagnostic of temporal event coverage, not independent throw F1.
"""

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def overlap(a, b) -> bool:
    return max(a[0], b[0]) <= min(a[1], b[1])


def score(review, ledger):
    if review["source_sha256"] != ledger["source_sha256"]:
        raise ValueError("Source hash mismatch")
    if review["independent_validation"]:
        raise ValueError("This scorer is only for source-only development review")

    uncertain = [event["interval_seconds"] for event in review["uncertain_boundary_events"]]
    if len({event["id"] for event in review["events"]}) != len(review["events"]):
        raise ValueError("Duplicate source-review event ID")
    if len({event["candidate_id"] for event in ledger["events"]}) != len(ledger["events"]):
        raise ValueError("Duplicate candidate ID")
    evaluated_spans = []
    for lo, hi in review["sampled_intervals_seconds"]:
        fragments = [(lo, hi)]
        for cut_lo, cut_hi in uncertain:
            next_fragments = []
            for start, end in fragments:
                if cut_hi <= start or end <= cut_lo:
                    next_fragments.append((start, end))
                else:
                    if start < cut_lo:
                        next_fragments.append((start, cut_lo))
                    if cut_hi < end:
                        next_fragments.append((cut_hi, end))
            fragments = next_fragments
        evaluated_spans.extend(fragments)

    def eligible(candidate):
        interval = candidate["release_window_s"]
        return (interval is not None and
                any(max(interval[0], lo) < min(interval[1], hi)
                    for lo, hi in evaluated_spans))

    labels = [event for event in review["events"] if event["status"] == "clear"]
    for label in labels:
        interval = label["delivery_interval_seconds"]
        if (interval[0] >= interval[1] or
                not any(lo <= interval[0] and interval[1] <= hi
                        for lo, hi in review["sampled_intervals_seconds"]) or
                any(max(interval[0], boundary[0]) < min(interval[1], boundary[1])
                    for boundary in uncertain)):
            raise ValueError(f"Clear event outside unambiguous sampled span: {label['id']}")
    candidates = [event for event in ledger["events"] if eligible(event)]
    edges = [
        [j for j, candidate in enumerate(candidates)
         if candidate["release_window_s"] is not None
         and overlap(label["delivery_interval_seconds"], candidate["release_window_s"])]
        for label in labels
    ]

    def maximum_matching(graph):
        owner = {}

        def augment(i, seen):
            for j in graph[i]:
                if j in seen:
                    continue
                seen.add(j)
                if j not in owner or augment(owner[j], seen):
                    owner[j] = i
                    return True
            return False

        for i in range(len(labels)):
            augment(i, set())
        return owner

    owner = maximum_matching(edges)
    colour_edges = [
        [j for j in adjacent if candidates[j]["colour"] == label["colour"]]
        for label, adjacent in zip(labels, edges)
    ]
    colour_owner = maximum_matching(colour_edges)
    by_label = {i: j for j, i in owner.items()}
    matches = []
    for i, j in sorted(by_label.items()):
        label, candidate = labels[i], candidates[j]
        matches.append({
            "label_id": label["id"],
            "candidate_id": candidate["candidate_id"],
            "label_colour": label["colour"],
            "candidate_colour": candidate["colour"],
            "colour_relation": "unknown" if candidate["colour"] is None else
                               "match" if label["colour"] == candidate["colour"] else "conflict",
        })
    tp = len(owner)
    fp = len(candidates) - tp
    fn = len(labels) - tp
    colour_tp = len(colour_owner)
    colour_fp = len(candidates) - colour_tp
    colour_fn = len(labels) - colour_tp
    return {
        "status": "development_diagnostic_not_independent_validation",
        "method": "One-to-one maximum-cardinality matching where candidate release window overlaps a clear source-only delivery interval; candidates selected when their release window overlaps an evaluable sampled span after uncertain boundaries are removed. No colour gate.",
        "clear_source_events": len(labels),
        "eligible_candidates": len(candidates),
        "temporal_true_positives": tp,
        "temporal_false_positives": fp,
        "temporal_false_negatives": fn,
        "temporal_precision": tp / (tp + fp) if tp + fp else None,
        "temporal_recall": tp / (tp + fn) if tp + fn else None,
        "temporal_f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None,
        "colour_aware_true_positives": colour_tp,
        "colour_aware_false_positives": colour_fp,
        "colour_aware_false_negatives": colour_fn,
        "colour_aware_precision": colour_tp / (colour_tp + colour_fp) if colour_tp + colour_fp else None,
        "colour_aware_recall": colour_tp / (colour_tp + colour_fn) if colour_tp + colour_fn else None,
        "colour_aware_f1": 2 * colour_tp / (2 * colour_tp + colour_fp + colour_fn)
                           if 2 * colour_tp + colour_fp + colour_fn else None,
        "matches": matches,
        "unmatched_candidate_ids": [candidate["candidate_id"] for j, candidate in enumerate(candidates) if j not in owner],
        "unmatched_label_ids": [label["id"] for i, label in enumerate(labels) if i not in by_label],
        "colour_aware_matches": [
            {"label_id": labels[i]["id"], "candidate_id": candidates[j]["candidate_id"]}
            for j, i in sorted(colour_owner.items(), key=lambda pair: pair[1])
        ],
        "limitations": [
            "Source labels were authored by the implementing agent from five-second samples and may miss off-camera deliveries.",
            "Broad candidate release windows can inflate temporal overlap and do not establish release-time accuracy.",
            "This is a small selected-window development check, not an independent full-match F1 estimate.",
        ],
    }


def with_colour_hypotheses(ledger, audit, ledger_hash):
    if audit["source_sha256"] != ledger["source_sha256"] or audit["ledger_sha256"] != ledger_hash:
        raise ValueError("Identity audit does not derive from this ledger")
    updated = deepcopy(ledger)
    by_id = {row["candidate_id"]: row for row in updated["events"]}
    applied = []
    for row in audit["rows"]:
        hypothesis = row["earliest_following_colour_hypothesis"]
        if hypothesis is None:
            continue
        candidate = by_id[row["candidate_id"]]
        if candidate["counter_id"] is not None:
            raise ValueError("Colour hypothesis cannot overwrite a counter-backed event")
        if candidate["colour"] != hypothesis:
            applied.append({"candidate_id": row["candidate_id"],
                            "ledger_colour": candidate["colour"],
                            "hypothesis_colour": hypothesis})
            candidate["colour"] = hypothesis
    return updated, applied


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--identity-audit", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    review = json.loads(args.review.read_text())
    ledger = json.loads(args.ledger.read_text())
    result = score(review, ledger)
    result["review_sha256"] = sha256(args.review)
    result["ledger_sha256"] = sha256(args.ledger)
    if args.identity_audit:
        audit = json.loads(args.identity_audit.read_text())
        variant, applied = with_colour_hypotheses(ledger, audit, result["ledger_sha256"])
        result["status"] = "postscore_development_colour_hypothesis_diagnostic"
        result["identity_audit_sha256"] = sha256(args.identity_audit)
        result["hypothesis_applied"] = applied
        result["hypothesis_score"] = score(review, variant)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: result[key] for key in (
        "clear_source_events", "eligible_candidates", "temporal_true_positives",
        "temporal_false_positives", "temporal_false_negatives", "temporal_f1",
        "unmatched_candidate_ids", "colour_aware_f1")}, indent=2))


if __name__ == "__main__":
    main()
