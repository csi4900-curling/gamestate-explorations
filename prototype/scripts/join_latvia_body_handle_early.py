"""Merge all sequential 1080p Latvia shards and link body-handle image paths."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype/scripts"))
from probe_latvia_1080p_body_paths import link_paths

BASE = ROOT / "validation/throw-event-benchmark/layout-router/full-2024-coverage/latvia24-full-v1"
CANDIDATES = BASE / "full-candidate-display-context-development.json"
OUT = BASE / "early-highres-body-handle-transfer-development.json"
START_S, STOP_S = 1650, 2760


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    if OUT.exists():
        raise SystemExit("Output exists; preserve first merged transfer")
    paths = sorted(BASE.glob("early-highres-body-handle-shard-*-sequential.json"))
    if not paths:
        raise RuntimeError("No sequential shards")
    shards = [json.loads(path.read_text()) for path in paths]
    fingerprints = {key: {item[key] for item in shards} for key in (
        "video_sha256", "candidate_ledger_sha256", "body_probe_sha256",
        "handle_screen_sha256", "body_code_sha256", "handle_code_sha256",
        "runner_sha256")}
    if any(len(values) != 1 for values in fingerprints.values()):
        raise ValueError("Shard provenance mismatch")
    if next(iter(fingerprints["candidate_ledger_sha256"])) != digest(CANDIDATES):
        raise ValueError("Candidate ledger differs from shards")
    rows_by_time = {}
    covered = set()
    for path, shard in zip(paths, shards):
        start, stop = shard["source_interval_s"]
        if not START_S <= start < stop <= STOP_S:
            raise ValueError(f"Shard interval outside source: {path}")
        seconds = set(range(start, stop))
        if covered & seconds:
            raise ValueError(f"Overlapping shard: {path}")
        covered |= seconds
        for row in shard["samples_with_body_proposals"]:
            t = row["time_s"]
            if t not in seconds or t in rows_by_time:
                raise ValueError(f"Duplicate/out-of-range source time: {t}")
            rows_by_time[t] = row
        if shard["body_proposal_count"] != sum(
                len(row["body_proposals"])
                for row in shard["samples_with_body_proposals"]):
            raise ValueError(f"Shard count mismatch: {path}")
    if covered != set(range(START_S, STOP_S)):
        raise ValueError("Shards do not cover full excerpt")
    samples = [rows_by_time.get(t, {"time_s": t, "body_proposals": []})
               for t in range(START_S, STOP_S)]
    screened = [
        {"time_s": row["time_s"],
         "body_proposals": [p for p in row["body_proposals"]
                            if p["handle_supported"]]}
        for row in samples]
    linked = link_paths(screened)
    ledger = json.loads(CANDIDATES.read_text())
    candidate_rows = [row for row in ledger["candidates"]
                      if START_S <= row["crossing_time_s"] < STOP_S and
                      row["observation_kind"] == "left_provisional_passage"]
    context = []
    for row in candidate_rows:
        t = row["crossing_time_s"]
        matched = [p["diagnostic_path_id"] for p in linked
                   if p["direction"] == "upward" and
                   t <= p["first_observed_s"] <= t+25]
        context.append({
            "candidate_id": row["candidate_id"],
            "crossing_time_s": t,
            "colour_claim": row["colour_claim"],
            "upward_body_handle_paths_started_within_25s": matched,
            "physical_throw_verified": False,
        })
    result = {
        "status": "full_early_excerpt_body_handle_development_transfer_not_event_validation",
        "source_interval_s": [START_S, STOP_S],
        "sample_period_s": 1,
        "source_video_sha256": next(iter(fingerprints["video_sha256"])),
        "candidate_ledger_sha256": digest(CANDIDATES),
        "joiner_sha256": digest(Path(__file__)),
        "linker_sha256": digest(
            ROOT / "prototype/scripts/probe_latvia_1080p_body_paths.py"),
        "shards": [{"path": str(path.relative_to(ROOT)),
                    "sha256": digest(path),
                    "interval_s": item["source_interval_s"]}
                   for path, item in zip(paths, shards)],
        "body_proposal_count": sum(len(row["body_proposals"]) for row in samples),
        "handle_supported_count": sum(len(row["body_proposals"]) for row in screened),
        "supported_path_direction_counts": dict(Counter(p["direction"] for p in linked)),
        "supported_image_paths": linked,
        "candidate_context": context,
        "candidate_count": len(context),
        "candidate_with_associated_upward_path_count": sum(
            bool(row["upward_body_handle_paths_started_within_25s"])
            for row in context),
        "limitations": [
            "The 2310 s moving yellow stone used to choose the template is inside this excerpt.",
            "Left candidate times are unverified model outputs, not independent throw labels.",
            "An associated upward image path can be a different object or physical event.",
            "Missing paths do not prove absence of a throw; occlusion and view changes remain.",
        ],
    }
    OUT.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"seconds": len(covered),
                      "body_proposals": result["body_proposal_count"],
                      "handle_supported": result["handle_supported_count"],
                      "paths": result["supported_path_direction_counts"],
                      "candidate_associations": result[
                          "candidate_with_associated_upward_path_count"],
                      "candidates": len(context)}))


if __name__ == "__main__":
    main()
