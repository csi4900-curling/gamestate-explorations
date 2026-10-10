"""Merge full late Latvia red-template shards and link image motion paths."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype/scripts"))
from probe_latvia_1080p_body_paths import link_paths

BASE = ROOT / "validation/throw-event-benchmark/layout-router/full-2024-coverage/latvia24-full-v1"
YELLOW = BASE / "end6-highres-body-handle-screen-development.json"
OUT = BASE / "end6-highres-red-full-transfer-development.json"
START_S, STOP_S = 5670, 6670


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    if OUT.exists():
        raise SystemExit("Output exists; preserve first full late red transfer")
    paths = sorted(BASE.glob("end6-highres-red-full-shard-*.json"))
    shards = [json.loads(path.read_text()) for path in paths]
    if len(shards) != 14:
        raise ValueError("Expected 14 bounded source shards")
    for key in (
        "source_video_sha256",
        "template_video_sha256",
        "red_template_audit_sha256",
        "runner_sha256",
        "body_code_sha256",
        "handle_code_sha256",
    ):
        if len({s[key] for s in shards}) != 1:
            raise ValueError(f"Shard provenance differs: {key}")
    yellow = json.loads(YELLOW.read_text())
    if yellow["blind_video_sha256"] != shards[0]["source_video_sha256"]:
        raise ValueError("Red and yellow probes used different late sources")
    covered, rows = set(), {}
    for path, shard in zip(paths, shards):
        start, stop = shard["source_interval_s"]
        span = set(range(start, stop))
        if not START_S <= start < stop <= STOP_S or covered & span:
            raise ValueError(f"Invalid or overlapping shard: {path}")
        covered |= span
        for row in shard["samples_with_body_proposals"]:
            if row["time_s"] not in span or row["time_s"] in rows:
                raise ValueError(f"Invalid or duplicate sample: {path}")
            rows[row["time_s"]] = row
        if shard["body_proposal_count"] != sum(
            len(r["body_proposals"]) for r in shard["samples_with_body_proposals"]
        ):
            raise ValueError(f"Shard count mismatch: {path}")
    if covered != set(range(START_S, STOP_S)):
        raise ValueError("Late interval coverage incomplete")
    samples = [rows.get(t, {"time_s": t, "body_proposals": []}) for t in range(START_S, STOP_S)]
    screened = [
        {
            "time_s": r["time_s"],
            "body_proposals": [p for p in r["body_proposals"] if p["red_handle_supported"]],
        }
        for r in samples
    ]
    linked = link_paths(screened)
    result = {
        "status": "late_blind_full_red_body_handle_development_not_throw_validation",
        "source_interval_s": [START_S, STOP_S],
        "sample_period_s": 1,
        "source_video_sha256": shards[0]["source_video_sha256"],
        "template_video_sha256": shards[0]["template_video_sha256"],
        "yellow_screen_sha256": digest(YELLOW),
        "joiner_sha256": digest(Path(__file__)),
        "linker_sha256": digest(ROOT / "prototype/scripts/probe_latvia_1080p_body_paths.py"),
        "shards": [
            {
                "path": str(path.relative_to(ROOT)),
                "sha256": digest(path),
                "interval_s": s["source_interval_s"],
            }
            for path, s in zip(paths, shards)
        ],
        "red_body_proposal_count": sum(len(r["body_proposals"]) for r in samples),
        "red_handle_supported_count": sum(len(r["body_proposals"]) for r in screened),
        "red_supported_path_direction_counts": dict(Counter(p["direction"] for p in linked)),
        "red_supported_image_paths": linked,
        "prior_yellow_supported_path_direction_counts": yellow["supported_path_direction_counts"],
        "limitations": [
            "Both colour lanes are same-match development probes, not independently scored detectors.",
            "An upward image path is a review candidate until source-visible stone and delivery are confirmed.",
            "No path does not prove no throw; the stone may be occluded or absent from this camera.",
            "Parked/handled stones can match either template and confuse temporal identity.",
        ],
    }
    OUT.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                "seconds": len(covered),
                "red_body": result["red_body_proposal_count"],
                "red_handle": result["red_handle_supported_count"],
                "red_paths": result["red_supported_path_direction_counts"],
                "yellow_paths": result["prior_yellow_supported_path_direction_counts"],
            }
        )
    )


if __name__ == "__main__":
    main()
