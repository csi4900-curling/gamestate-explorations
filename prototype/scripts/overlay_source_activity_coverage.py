"""Export a source-hashed active-static-panel coverage overlay."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256
from source_activity_coverage import overlay_active_static_left


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeline", type=Path, required=True)
    parser.add_argument("--activity-audit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    timeline = json.loads(args.timeline.read_text())
    audit = json.loads(args.activity_audit.read_text())
    result = overlay_active_static_left(timeline, audit)
    result["timeline_sha256"] = file_sha256(args.timeline)
    result["activity_audit_sha256"] = file_sha256(args.activity_audit)
    result["overlay_code_sha256"] = file_sha256(ROOT / "prototype/source_activity_coverage.py")
    result["runner_sha256"] = file_sha256(Path(__file__))
    result["limitations"] = [
        "The active-static thresholds were chosen after inspecting Latvia and Italy source frames.",
        "A static left panel can be a still camera view or frozen feed; this audit does not distinguish them.",
        "Source-image activity does not label individual delivered stones or estimate throw F1.",
        "Original candidate events are preserved, including any that fall inside a newly unsupported interval.",
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(
        {
            key: result[key]
            for key in (
                "newly_unsupported_seconds",
                "revised_supported_seconds",
                "revised_unknown_seconds",
            )
        }
    )


if __name__ == "__main__":
    main()
