"""Audit delayed counter-to-shot associations on an exposed interval."""

import argparse
import hashlib
import json
from pathlib import Path

from prototype.counter_shot_alignment import align_counter_events, rescue_following_only


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shot-score", required=True, type=Path)
    parser.add_argument("--counter-audit", required=True, type=Path)
    parser.add_argument("--motion-audit", action="append", required=True, type=Path)
    parser.add_argument(
        "--rescue-following-only",
        action="store_true",
        help="Try strong-origin, dual-channel motion after the cut",
    )
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    score = json.loads(args.shot_score.read_text())
    counter = json.loads(args.counter_audit.read_text())
    if score["source_sha256"] != counter["source_sha256"]:
        raise ValueError("Shot score and counter source differ")
    motion = {}
    motion_hashes = {}
    for path in args.motion_audit:
        audit = json.loads(path.read_text())
        if audit["source_sha256"] != score["source_sha256"]:
            raise ValueError(f"Motion audit source differs: {path}")
        if audit["source_interval_s"] != score["source_interval_s"]:
            raise ValueError(f"Motion audit interval differs: {path}")
        if path.stem in motion:
            raise ValueError(f"Duplicate motion channel: {path.stem}")
        motion[path.stem] = audit["shots"]
        motion_hashes[path.stem] = sha256(path)
    begin, end = score["source_interval_s"]
    events = [row for row in counter["counter_events"] if begin <= row["crossing_time_s"] < end]
    rows = align_counter_events(score["rows"], events, motion)
    if args.rescue_following_only:
        rows = rescue_following_only(rows, score["rows"], motion)
    labels = {row["shot_id"]: row["label"] for row in score["rows"]}
    for row in rows:
        row["development_label"] = labels[row["shot_id"]] if row["shot_id"] else None
    associated = [row for row in rows if row["shot_id"]]
    labelled = any(value in (0, 1) for value in labels.values())
    result = {
        "status": "postscore_development_counter_shot_alignment_with_following_only_rescue"
        if args.rescue_following_only
        else "development_counter_shot_alignment_audit",
        "source_sha256": score["source_sha256"],
        "source_interval_s": score["source_interval_s"],
        "shot_score_sha256": sha256(args.shot_score),
        "counter_audit_sha256": sha256(args.counter_audit),
        "motion_audit_sha256": motion_hashes,
        "alignment_code_sha256": sha256(
            Path(__file__).resolve().parents[1] / "counter_shot_alignment.py"
        ),
        "runner_sha256": sha256(Path(__file__)),
        "counter_event_count": len(events),
        "following_only_rescue_enabled": args.rescue_following_only,
        "associated_count": len(associated),
        "associated_agent_positive_count": (
            sum(row["development_label"] == 1 for row in associated) if labelled else None
        ),
        "rows": rows,
        "limitations": [
            "This is a postscore development audit on exposed footage, not held-out F1.",
            "Counter updates are delayed and not always visible; no update is not evidence of no throw.",
            "Shot labels are agent-authored and were used only after association for auditing.",
            "A shot association does not locate release time or prove physical stone identity.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(
        f"{args.output}: {len(associated)}/{len(events)} associated, "
        f"agent-positive={result['associated_agent_positive_count']}"
    )


if __name__ == "__main__":
    main()
