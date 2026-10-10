"""Find identical motion tracks attributed to multiple Norway candidates."""

from collections import defaultdict
from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "validation/official-shot-sequence/norway-full-event-motion-transfer-first.json"
OUTPUT = ROOT / "validation/official-shot-sequence/norway-motion-track-reuse-first.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first track-reuse audit")
    source = json.loads(SOURCE.read_text())
    occurrences = defaultdict(list)
    for event in source["rows"]:
        for colour in ("red", "yellow"):
            for track in event["colour_tracks"][colour]:
                key = (colour, track["first_seen_s"], track["last_seen_s"],
                       track["span_px"])
                occurrences[key].append({"shot_id": event["shot_id"],
                                         "counter_id": event["counter_id"],
                                         "delivery_window_s": event["delivery_window_s"]})
    reused = [{"colour": key[0], "motion_interval_s": [key[1], key[2]],
               "span_px": key[3], "candidate_events": events}
              for key, events in sorted(occurrences.items(), key=lambda pair: pair[0][1])
              if len(events) > 1]
    result = {"status": "source_only_exact_motion_track_reuse_audit",
              "motion_transfer_sha256": digest(SOURCE),
              "runner_sha256": digest(Path(__file__)),
              "track_attribution_count": sum(len(events) for events in occurrences.values()),
              "distinct_exact_track_count": len(occurrences),
              "reused_exact_track_count": len(reused),
              "candidate_events_in_reused_tracks": len({event["shot_id"] for row in reused
                                                       for event in row["candidate_events"]}),
              "rows": reused,
              "limitations": ["Exact track equality is a lower bound on reuse; shifted search windows can fragment the same stone track.",
                              "A shared track proves candidate support is not independent, not which candidate is correct.",
                              "Neither candidate ledger nor tracks are independently labelled physical throws."]}
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print({key: result[key] for key in ("track_attribution_count", "distinct_exact_track_count",
                                           "reused_exact_track_count", "candidate_events_in_reused_tracks")})


if __name__ == "__main__":
    main()
