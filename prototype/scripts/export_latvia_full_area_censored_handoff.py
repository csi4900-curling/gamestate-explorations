"""Export the ordered Latvia full-match and late right-area review union."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from full_match_area_censored_handoff import build_full_match_area_censored_handoff


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("legacy", "late-censored", "withheld-audit",
                 "accepted-no-right-audit", "lowres-video",
                 "highres-video", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists")
    legacy = json.loads(args.legacy.read_text())
    late = json.loads(args.late_censored.read_text())
    audit = json.loads(args.withheld_audit.read_text())
    no_right = json.loads(args.accepted_no_right_audit.read_text())
    if (digest(args.lowres_video) != legacy["source_sha256"] or
            digest(args.highres_video) != late["source_video_sha256"][
                "highres"] or digest(args.lowres_video) != audit[
                    "source_video_sha256"] or digest(args.lowres_video) !=
            no_right["source_video_sha256"]):
        raise ValueError("Source video fingerprint differs")
    output = build_full_match_area_censored_handoff(legacy, late, audit,
                                                    no_right)
    output["provenance"] = {
        "input_sha256": {"legacy": digest(args.legacy),
                         "late_censored": digest(args.late_censored),
                         "withheld_audit": digest(args.withheld_audit),
                         "accepted_no_right_audit": digest(
                             args.accepted_no_right_audit)},
        "source_video_sha256": {
            "lowres": digest(args.lowres_video),
            "highres_late_excerpt": digest(args.highres_video)},
        "model_code_sha256": digest(
            ROOT / "prototype/full_match_area_censored_handoff.py"),
        "runner_sha256": digest(Path(__file__)),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({"candidates": output["candidate_count"],
                      "kinds": output["candidate_counts_by_kind"],
                      "possible_event_reviews": output[
                          "development_possible_event_review_count"],
                      "physical_throw_count_verified": None}))


if __name__ == "__main__":
    main()
