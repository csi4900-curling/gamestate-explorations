"""Postscore overlap of exact-transit China track quality with counters."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/curlobserver-learned-probe/cap-patch-crossmatch-v1"
FULL = ROOT / "validation/curlobserver-learned-probe/china-full-transfer"
FIRST = BASE / "china-cap-track-quality-full-v2-first.json"
ALIGNMENT = FULL / "counter-shot-alignment.json"
OUTPUT = BASE / "china-cap-track-quality-overlap-v2-postscore.json"


def digest(path):
    h = sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first postscore overlap")
    first = json.loads(FIRST.read_text())
    alignment = json.loads(ALIGNMENT.read_text())
    if first["sha256"]["video"] != alignment["source_sha256"]:
        raise ValueError("Source fingerprint mismatch")
    linked = {}
    for counter in alignment["rows"]:
        if counter["status"] == "associated" and counter["shot_id"]:
            linked.setdefault(counter["shot_id"], []).append(counter["counter_id"])
    rows = []
    for quality in sorted(set(row["quality"] for row in first["rows"])):
        members = [row for row in first["rows"] if row["quality"] == quality]
        associated = [row for row in members if row["shot_id"] in linked]
        rows.append({
            "quality": quality,
            "candidate_window_count": len(members),
            "counter_associated_window_count": len(associated),
            "shot_ids": [row["shot_id"] for row in members],
            "counter_associated_shot_ids": [row["shot_id"] for row in associated],
        })
    known_linked = [row for row in first["rows"]
                    if row["colour"] is not None and row["shot_id"] in linked]
    supported_linked = [row for row in known_linked
                        if row["quality"] == "combined_cue_supported"]
    output = {
        "status": "postscore_china_exact_transit_track_quality_counter_overlap_not_event_score",
        "first_sha256": digest(FIRST),
        "counter_alignment_sha256": digest(ALIGNMENT),
        "runner_sha256": digest(__file__),
        "candidate_window_count": len(first["rows"]),
        "quality_counts": dict(Counter(row["quality"] for row in first["rows"])),
        "known_colour_counter_associated_window_count": len(known_linked),
        "combined_supported_counter_associated_window_count": len(supported_linked),
        "rows": rows,
        "interpretation": (
            "A hard combined-cue gate would retain only the supported subset of "
            "already counter-associated known-colour windows; this is a coverage "
            "warning, not an event precision or recall estimate."
        ),
        "limitations": [
            "Counter association is delayed and is itself conditioned on same-colour motion in adjacent shots.",
            "Counter-linked windows are not exhaustive physical throw ground truth.",
            "The selected top short transit may not be the delivered stone even when a counter is associated.",
            "The source-only first audit did not read this counter alignment.",
        ],
    }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n")
    print({"known_colour_counter_associated": len(known_linked),
           "combined_supported": len(supported_linked),
           "quality_counts": output["quality_counts"]})


if __name__ == "__main__":
    main()
