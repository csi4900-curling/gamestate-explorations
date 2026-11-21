"""Compare saved two-sample roles with a four-sample motion diagnostic on development data."""

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
from statistics import median


def four_sample_role(samples, bracket, step):
    offsets = [index for index, sample in enumerate(samples) if sample["time_s"] == bracket[0]]
    if len(offsets) != 1 or offsets[0] < 1:
        return "unassigned"
    window = samples[offsets[0]-1:offsets[0]+3]
    if len(window) != 4 or window[2]["time_s"] != bracket[1]:
        return "unassigned"
    if any(not math.isclose(right["time_s"]-left["time_s"], step, abs_tol=1e-6)
           for left, right in zip(window, window[1:])):
        return "unassigned"
    positions = [sample.get("conditional_height_adjusted_position_m") for sample in window]
    if any(position is None or not math.isfinite(position[1]) for position in positions):
        return "unassigned"
    longitudinal = [position[1] for position in positions]
    if min(longitudinal) <= 0 <= max(longitudinal):
        return "unassigned"
    delta = median(abs(right)-abs(left) for left, right in zip(longitudinal, longitudinal[1:]))
    return "departure" if delta > 0 else "receiving" if delta < 0 else "unassigned"


def audit(path, step, observations=None):
    with path.open("rb") as stream:
        checksum = hashlib.file_digest(stream, "sha256").hexdigest()
        stream.seek(0)
        aggregate = json.load(stream)
    events = aggregate["events"]
    transitions = Counter()
    changed = []
    alternatives = {}
    for event in events:
        primary, = [segment for segment in event["segments"] if segment["segment_id"].endswith(":primary")]
        previous = primary["role"]
        alternative = four_sample_role(primary["geometry_samples"], event["event_prediction"]["observed_bracket_s"], step)
        transitions[f"{previous} -> {alternative}"] += 1
        alternatives[event["candidate_id"]] = {"role": alternative, "panel": primary.get("rink_panel")}
        if alternative != previous:
            changed.append((event["candidate_id"], previous, alternative))
    result = {"aggregate": str(path), "sha256": checksum, "step_s": step, "events": len(events),
            "transitions": dict(transitions), "changed": changed,
            "scope": "Development component comparison; no event labels, inferred links or identity accuracy."}
    if observations is not None:
        from prototype.directional_handoff import hypotheses, metric_crossings
        payload = json.loads((observations/"events.json").read_text())
        if payload["source_sha256"] != aggregate["provenance"]["source_sha256"]:
            raise ValueError("Event source differs from aggregate")
        board_path = observations/"match-observations.jsonl"
        result["input_sha256"] = {"boards": checksum_file(board_path), "events": checksum_file(observations/"events.json")}
        with board_path.open() as stream:
            crossings = metric_crossings(map(json.loads, stream), hog_y_by_panel=aggregate["rink_transform"]["hog_y_m"])
        baseline = {event["candidate_id"]: event["handoff_hypothesis"]["role_evidence"] for event in events}
        def replay(roles):
            records = hypotheses(payload["events"], roles, crossings, payload["source_interval_s"])
            return {key: signature(record) for key, record in records.items()}
        def signature(record):
            return record["status"], [candidate["id"] for candidate in record["candidates"]]
        before = replay(baseline)
        if before != {event["candidate_id"]: signature(event["handoff_hypothesis"]) for event in events}:
            raise ValueError("Baseline handoff hypotheses did not reproduce")
        after = replay(alternatives)
        result["handoff_hypothesis_changes"] = {key: [before[key], after[key]] for key in before if before[key] != after[key]}
    return result


def checksum_file(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("aggregate", type=Path)
    parser.add_argument("--step-s", type=float, required=True)
    parser.add_argument("--observations", type=Path)
    args = parser.parse_args()
    print(json.dumps(audit(args.aggregate, args.step_s, args.observations), indent=2))
