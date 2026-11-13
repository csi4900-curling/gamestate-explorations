"""Compare descriptive raw-underpoint tiers on Czech and Latvia sources."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark/layout-router"
INPUTS = {
    "czech_2024_full_supported_run": BASE
    / "czech24-full-camera-motion-v1/run-02/raw-underpoint-context-development.json",
    "latvia_2024_1650_2760": BASE
    / "latvia24-1650-2760-raw-context-v1/raw-underpoint-context-development.json",
}
OUT = BASE / "raw-underpoint-cross-recording-development.json"


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def summary(rows):
    values = [r["median_nonice_fraction"] for r in rows]
    if any(value is None for value in values):
        raise ValueError("Unmeasured candidate in transfer comparison")
    tier = lambda value: (
        "clear" if value <= 0.05 else ("cluttered" if value > 0.25 else "ambiguous")
    )
    return {
        "candidate_count": len(rows),
        "median_nonice_fraction": round(statistics.median(values), 6),
        "tier_counts": dict(Counter(tier(value) for value in values)),
    }


def main():
    if OUT.exists():
        raise ValueError("Transfer summary exists")
    data = {name: json.loads(path.read_text()) for name, path in INPUTS.items()}
    code_hash = digest(ROOT / "prototype/highres_underpoint_context.py")
    if (
        len({d["feature_code_sha256"] for d in data.values()}) != 1
        or next(iter(data.values()))["feature_code_sha256"] != code_hash
    ):
        raise ValueError("Feature code differs between recordings")
    if len({d["sample_strategy"] for d in data.values()}) != 1:
        raise ValueError("Sampling strategy differs between recordings")
    rows = {}
    for name, document in data.items():
        if len(document["rows"]) != document["summary"]["raw_proposals"]:
            raise ValueError("Candidate inventory incomplete")
        rows[name] = {
            "all": summary(document["rows"]),
            "context_confirmed": summary([r for r in document["rows"] if r["context_confirmed"]]),
            "context_withheld": summary(
                [r for r in document["rows"] if not r["context_confirmed"]]
            ),
        }
    OUT.write_text(
        json.dumps(
            {
                "status": "development_raw_context_cross_recording_comparison_not_throw_accuracy",
                "input_sha256": {name: digest(path) for name, path in INPUTS.items()},
                "feature_code_sha256": code_hash,
                "runner_sha256": digest(Path(__file__)),
                "descriptive_boundaries": {"clear_max": 0.05, "cluttered_above": 0.25},
                "rows": rows,
                "limitations": [
                    "Both recordings and the descriptive boundaries were exposed during development.",
                    "Context confirmation is a detector decision, not physical stone or throw truth.",
                    "The samples measure raw pre-confirmation caps, not the later receiving-view body paths where the boundaries were chosen.",
                ],
            },
            indent=2,
        )
        + "\n"
    )
    print(json.dumps(rows))


if __name__ == "__main__":
    main()
