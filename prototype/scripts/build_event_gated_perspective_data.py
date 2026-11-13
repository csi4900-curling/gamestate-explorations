"""Package source-video state observations for the offline perspective viewer."""

from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "validation/official-shot-sequence/event-gated-video-state-observations-first.json"
OUTPUT = ROOT / "prototype/full-match-canada-china/event-gated-state-data.js"


def main():
    state = json.loads(SOURCE.read_text())
    china = next(r for r in state["recordings"] if r["recording_code"] == "PREL000102")
    if china["event_count"] != 125 or china["partial_board_count"] != 59:
        raise ValueError("Source-only state export changed; review demo text")
    payload = {
        "source_export_sha256": sha256(SOURCE.read_bytes()).hexdigest(),
        "recording_code": china["recording_code"],
        "source_video_sha256": china["source_video_sha256"],
        "event_count": china["event_count"],
        "partial_board_count": china["partial_board_count"],
        "rows": china["rows"],
    }
    OUTPUT.write_text(
        "const EXPERIMENTAL_VIDEO_STATES = "
        + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        + ";\n"
    )
    print(
        {
            "events": payload["event_count"],
            "boards": payload["partial_board_count"],
            "output": str(OUTPUT),
        }
    )


if __name__ == "__main__":
    main()
