"""Audit coverage and summarize all nine red candidate-window probes."""

from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark/layout-router/full-2024-coverage/latvia24-full-v1"
LEDGER = BASE / "full-candidate-display-context-development.json"
SOURCE_REVIEW = BASE / "early-highres-red-upward-source-review.json"
OUT = BASE / "early-highres-red-candidate-window-summary-development.json"


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    if OUT.exists():
        raise SystemExit("Output exists; preserve first summary")
    ledger = json.loads(LEDGER.read_text())
    expected = {
        r["candidate_id"]
        for r in ledger["candidates"]
        if r["observation_kind"] == "left_provisional_passage"
        and r["colour_claim"] == "red"
        and 1650 <= r["crossing_time_s"] < 2760
    }
    paths = sorted(BASE.glob("early-highres-red-window-S*.json"))
    windows = [json.loads(path.read_text()) for path in paths]
    if {r["candidate_id"] for r in windows} != expected or len(windows) != len(expected):
        raise ValueError("Red window coverage differs from candidate ledger")
    for key in (
        "source_video_sha256",
        "candidate_ledger_sha256",
        "red_template_audit_sha256",
        "runner_sha256",
        "body_code_sha256",
        "handle_code_sha256",
    ):
        if len({r[key] for r in windows}) != 1:
            raise ValueError(f"Window provenance differs: {key}")
    if windows[0]["candidate_ledger_sha256"] != digest(LEDGER):
        raise ValueError("Candidate ledger changed")
    review = json.loads(SOURCE_REVIEW.read_text())
    if {r["candidate_id"] for r in review["paths"]} != {
        r["candidate_id"] for r in windows if r["upward_path_count"]
    }:
        raise ValueError("Source review does not cover all upward windows")
    rows = []
    for path, window in zip(paths, windows):
        suffix = window["candidate_id"].split("-")[-1]
        rows.append(
            {
                "candidate_id": window["candidate_id"],
                "window_sha256": digest(path),
                "source_interval_s": window["source_interval_s"],
                "body_proposal_count": window["body_proposal_count"],
                "red_handle_supported_count": window["red_handle_supported_count"],
                "upward_path_count": window["upward_path_count"],
                "same_agent_moving_red_source_review": (
                    review["same_agent_source_review"].get(suffix, {}).get("moving_prefix")
                    == "source_visible_moving_red_stone"
                ),
            }
        )
    result = {
        "status": "prediction_targeted_nine_red_window_development_summary_not_event_recall",
        "candidate_ledger_sha256": digest(LEDGER),
        "source_review_sha256": digest(SOURCE_REVIEW),
        "joiner_sha256": digest(Path(__file__)),
        "window_count": len(rows),
        "windows_with_upward_path": sum(r["upward_path_count"] > 0 for r in rows),
        "windows_with_source_visible_moving_red_prefix": sum(
            r["same_agent_moving_red_source_review"] for r in rows
        ),
        "template_source_window": "left:R01-S49",
        "windows": rows,
        "limitations": [
            "Windows are selected from provisional model candidates rather than exhaustive source labels.",
            "The source-template event S49 is included in the six supported windows.",
            "A moving prefix does not verify persistent identity or settled board state.",
            "No full-excerpt false-positive rate, independent throw precision or recall is measured.",
        ],
    }
    OUT.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                "windows": len(rows),
                "upward": result["windows_with_upward_path"],
                "source_reviewed": result["windows_with_source_visible_moving_red_prefix"],
            }
        )
    )


if __name__ == "__main__":
    main()
