"""Merge routed raw left candidates with right-only review entries."""

import argparse
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256
from candidate_review_union import build_candidate_review_union
from two_stage_throw_triage import triage_candidates


def load_left_sources(timeline_path, timeline):
    """Use saved triage, or reconstruct it from its frozen raw/confirmed pair."""
    left_by_run = {}
    triage_hashes = {}
    reconstructed = {}
    raw_hashes = {}
    for run in timeline["supported_runs"]:
        if run["layout"] != "split_2024":
            continue
        event_path = timeline_path.parent / run["adapter_artifact"]
        triage_path = event_path.with_name("triage.json")
        raw_path = event_path.with_name("raw.json")
        raw = json.loads(raw_path.read_text())
        raw_hash = file_sha256(raw_path)
        if (raw["source_sha256"] != timeline["source_sha256"] or
                raw["source_interval_s"] != run["interval_s"]):
            raise ValueError(f"Saved raw source differs: {run['id']}")
        if triage_path.exists():
            triage = json.loads(triage_path.read_text())
            if (triage["source_sha256"] != timeline["source_sha256"] or
                    triage["source_interval_s"] != run["interval_s"] or
                    triage["confirmation_sha256"] != file_sha256(event_path) or
                    triage["raw_sha256"] != raw_hash):
                raise ValueError(f"Left triage source or confirmation differs: {run['id']}")
            proposals = triage["proposals"]
            triage_hashes[run["id"]] = file_sha256(triage_path)
        else:
            confirmed = json.loads(event_path.read_text())
            if any(doc["source_sha256"] != timeline["source_sha256"] or
                   doc["source_interval_s"] != run["interval_s"]
                   for doc in (raw, confirmed)):
                raise ValueError(f"Saved raw and confirmed source differ: {run['id']}")
            proposals = triage_candidates(raw["events"],
                                          [("span_context", confirmed)])["proposals"]
            reconstructed[run["id"]] = {
                "raw_sha256": raw_hash,
                "confirmation_sha256": file_sha256(event_path),
                "triage_code_sha256": file_sha256(
                    ROOT / "prototype/two_stage_throw_triage.py"),
            }
        if len({p["id"] for p in proposals}) != len(proposals):
            raise ValueError(f"Duplicate raw left proposal in {run['id']}")
        raw_by_id = {event["id"]: event for event in raw["events"]}
        if len(raw_by_id) != len(raw["events"]) or set(raw_by_id) != {
                proposal["id"] for proposal in proposals}:
            raise ValueError(f"Raw and triaged proposal IDs differ: {run['id']}")
        enriched = []
        for proposal in proposals:
            event = raw_by_id[proposal["id"]]
            start, stop, crossing = (event["first_observed_s"],
                                     event["confirmed_at_s"],
                                     proposal["crossing_time_s"])
            if (not all(isinstance(t, (int, float)) and math.isfinite(t)
                        for t in (start, stop, crossing)) or
                    not start <= crossing <= stop):
                raise ValueError(f"Invalid left observed interval: {run['id']}-{proposal['id']}")
            enriched.append({**proposal,
                             "observed_motion_interval_s": [start, stop]})
        left_by_run[run["id"]] = enriched
        raw_hashes[run["id"]] = raw_hash
    return left_by_run, triage_hashes, reconstructed, raw_hashes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeline", type=Path, required=True)
    parser.add_argument("--fusion", type=Path, required=True)
    parser.add_argument("--coverage", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    timeline = json.loads(args.timeline.read_text())
    fusion = json.loads(args.fusion.read_text())
    coverage = json.loads(args.coverage.read_text())
    if (fusion["left_sha256"] != file_sha256(args.timeline) or
            fusion["coverage_sha256"] != file_sha256(args.coverage) or
            coverage["source_sha256"] != timeline["source_sha256"]):
        raise ValueError("Candidate review input chain differs")
    left_by_run, triage_hashes, reconstructed, raw_hashes = load_left_sources(
        args.timeline, timeline)
    result = build_candidate_review_union(timeline, left_by_run, fusion)
    result["layout_coverage_gaps_s"] = timeline["coverage_gaps_s"]
    result["left_trigger_blind_intervals_s"] = [
        row["interval_s"] for row in coverage["newly_unsupported_intervals"]]
    result["input_sha256"] = {
        "timeline": file_sha256(args.timeline),
        "fusion": file_sha256(args.fusion),
        "coverage": file_sha256(args.coverage),
        "left_triage_by_run": triage_hashes,
        "left_raw_by_run": raw_hashes,
    }
    if reconstructed:
        result["input_sha256"]["left_reconstructed_by_run"] = reconstructed
    result["model_code_sha256"] = file_sha256(ROOT / "prototype/candidate_review_union.py")
    result["runner_sha256"] = file_sha256(Path(__file__))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as file:
        file.write(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"candidates": result["candidate_count"],
                      "statuses": result["review_status_counts"]}))


if __name__ == "__main__":
    main()
