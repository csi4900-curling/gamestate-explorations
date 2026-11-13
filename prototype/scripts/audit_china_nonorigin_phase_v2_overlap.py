"""Post-transfer overlap diagnostic; do not revise the frozen first candidate list."""

from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STUDY = ROOT / "validation/curlobserver-learned-probe/cap-patch-crossmatch-v1"
FIRST = STUDY / "china-nonorigin-phase-v2-first.json"
LEDGER = (
    ROOT / "validation/curlobserver-learned-probe/china-full-transfer/"
    "candidate-throw-event-ledger-after-link.json"
)
OUTPUT = STUDY / "china-nonorigin-phase-v2-overlap-postscore.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def counter_colour(counter):
    if counter is None:
        return None
    before, after = counter["remaining_before"], counter["remaining_after"]
    drops = [
        name for index, name in enumerate(("red", "yellow")) if before[index] - after[index] == 1
    ]
    return drops[0] if len(drops) == 1 else None


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first overlap diagnostic")
    first, ledger = (json.loads(path.read_text()) for path in (FIRST, LEDGER))
    if first["source_sha256"] != ledger["source_sha256"]:
        raise ValueError("Source fingerprint mismatch")
    by_shot = {}
    for event in ledger["events"]:
        by_shot.setdefault(event.get("shot_id"), []).append(event)
    rows = []
    for candidate in first["candidates"]:
        existing = by_shot.get(candidate["shot_id"], [])
        rows.append(
            {
                "shot_id": candidate["shot_id"],
                "fallback_colour": candidate["colour"],
                "fallback_interval_s": candidate["interval_s"],
                "existing_visual_candidates": [
                    {
                        "candidate_id": row["candidate_id"],
                        "colour": row["colour"],
                        "colour_status": row["colour_status"],
                        "counter_id": row["counter_id"],
                        "counter_colour": counter_colour(row.get("broadcast_counter")),
                    }
                    for row in existing
                ],
                "novel_camera_shot": not existing,
                "contradicts_linked_counter_colour": any(
                    counter_colour(row.get("broadcast_counter")) not in (None, candidate["colour"])
                    for row in existing
                ),
            }
        )
    output = {
        "status": "postscore_overlap_of_frozen_china_fallback_not_new_event_score",
        "source_sha256": first["source_sha256"],
        "first_transfer_sha256": digest(FIRST),
        "existing_ledger_sha256": digest(LEDGER),
        "runner_sha256": digest(Path(__file__)),
        "fallback_candidate_count": len(rows),
        "novel_camera_shot_count": sum(row["novel_camera_shot"] for row in rows),
        "linked_counter_colour_conflict_count": sum(
            row["contradicts_linked_counter_colour"] for row in rows
        ),
        "rows": rows,
        "limitations": [
            "The existing ledger and its counter links are weak, not independent physical throw labels.",
            "A same-shot overlap proves the fallback adds no new shot window, not that the visual candidate is true or false.",
            "The China fallback first output remains frozen and unpromoted.",
        ],
    }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n")
    print(
        {
            "fallback": len(rows),
            "novel": output["novel_camera_shot_count"],
            "counter_colour_conflicts": output["linked_counter_colour_conflict_count"],
        }
    )


if __name__ == "__main__":
    main()
