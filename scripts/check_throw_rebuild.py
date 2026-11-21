"""Compare completed workbench output rebuilds on the same observation stream."""

import argparse
import hashlib
import json
from pathlib import Path


def read(job, name):
    return json.loads((job / name).read_text())


def check(baseline, rebuilt):
    if baseline.resolve() == rebuilt.resolve():
        raise ValueError("Use separate baseline and rebuilt jobs")
    hashes = []
    events = []
    for job in (baseline, rebuilt):
        if read(job, "job.json")["state"] != "done":
            raise ValueError(f"Incomplete job: {job}")
        with (job / "observations/match-observations.jsonl").open("rb") as stream:
            hashes.append(hashlib.file_digest(stream, "sha256").hexdigest())
        events.append(read(job, "result/aggregate-rink.json")["events"])
    if hashes[0] != hashes[1] or events[0] != events[1]:
        raise ValueError("Observations or full trajectory events differ; inspect before accepting regression")
    view = read(rebuilt, "result/aggregate-rink-throw-extent.json")["events"]
    if [event["candidate_id"] for event in view] != [event["candidate_id"] for event in events[1]]:
        raise ValueError("Display omitted or reordered candidates")
    for event in view:
        for segment in event["segments"]:
            points = [sample for sample in segment["geometry_samples"] if sample.get("rink_position_m") is not None]
            for prefix, point in (("first", points[0] if points else {}), ("last", points[-1] if points else {})):
                if (segment[f"rink_{prefix}_time_s"] != point.get("time_s")
                        or segment[f"rink_{prefix}_m"] != point.get("rink_position_m")
                        or segment["rink_sample_count"] != len(points)):
                    raise ValueError(f"Inconsistent displayed geometry: {segment['segment_id']}")
    print(f"{len(view)} candidate records preserved; display endpoints consistent. Observations SHA-256: {hashes[0]}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("rebuilt", type=Path)
    arguments = parser.parse_args()
    check(arguments.baseline, arguments.rebuilt)
