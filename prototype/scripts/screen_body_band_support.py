"""Apply the predeclared 0.5 neutral-gray body-band abstention in development."""

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from body_band_abstention import apply_body_band_abstention  # noqa: E402
from cache_contract import file_sha256  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--screen", type=Path, required=True)
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Development screen already exists")
    screen = json.loads(args.screen.read_text())
    features = json.loads(args.features.read_text())
    if (
        features["screen_sha256"] != file_sha256(args.screen)
        or features["source_sha256"] != screen["source_sha256"]
        or features["accepted_candidate_count"] != len(features["rows"])
    ):
        parser.error("Feature audit does not chain to frozen screen")
    derived = apply_body_band_abstention(screen, features, threshold=0.5)
    output = {
        "status": "postscore_development_body_band_abstention_not_independent_validation",
        "source_id": screen["source_id"],
        "source_sha256": screen["source_sha256"],
        "source_interval_s": screen["source_interval_s"],
        "frozen_screen_sha256": file_sha256(args.screen),
        "feature_audit_sha256": file_sha256(args.features),
        "rule_code_sha256": file_sha256(ROOT / "prototype/body_band_abstention.py"),
        "runner_sha256": file_sha256(Path(__file__)),
        "neutral_gray_fraction_threshold": 0.5,
        **derived,
        "limitations": [
            "The feature and threshold were developed after inspecting S96 and S143 on the exposed Canada-Czechia match.",
            "An abstention is not a verified false positive and does not establish recall or F1.",
            "Transferred accepted candidates are provisional; absence of new flags is not a false-negative measurement.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print(
        derived["frozen_accepted_count"],
        "->",
        derived["development_accepted_count"],
        "accepted; flagged",
        derived["flagged_candidate_ids"],
    )


if __name__ == "__main__":
    main()
