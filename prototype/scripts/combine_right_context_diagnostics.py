"""Join frozen ring and underpoint measurements on reviewed 2024 prefixes."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

RING_THRESHOLD = 0.25
UNDERPOINT_THRESHOLD = 0.25


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def source_class(name):
    if name in ("moving_stone", "moving_stone_short_path"):
        return "moving_stone_prefix"
    if name in (
        "person_or_wheelchair",
        "person_wheelchair_or_clothing",
        "moving_person_wheelchair",
        "person_or_wheelchair_or_equipment",
    ):
        return "person_or_equipment_prefix"
    if name == "stone_moved_by_person":
        return "nonthrow_stone_handling_prefix"
    if name == "stone_pixels_identity_uncertain":
        return "stone_pixels_identity_uncertain"
    if name == "mixed_stone_to_person_identity_switch":
        return "mixed_identity_prefix"
    raise ValueError(f"Unknown source class {name}")


def join_pair(name, ring_path, underpoint_path):
    ring = json.loads(ring_path.read_text())
    underpoint = json.loads(underpoint_path.read_text())
    if (
        ring["source_sha256"] != underpoint["source_sha256"]
        or ring["source_review_sha256"] != underpoint["source_review_sha256"]
    ):
        raise ValueError(f"{name}: mismatched source/review fingerprints")
    if (
        ring.get("proposals_sha256", ring.get("variant_sha256", ring.get("probe_sha256")))
        != underpoint["proposals_sha256"]
    ):
        raise ValueError(f"{name}: mismatched proposals fingerprint")
    ring_rows = {
        row.get("raw_track_id", row.get("right_raw_track_id")): row for row in ring["rows"]
    }
    under_rows = {row["raw_track_id"]: row for row in underpoint["rows"]}
    if (
        len(ring_rows) != len(ring["rows"])
        or len(under_rows) != len(underpoint["rows"])
        or set(ring_rows) != set(under_rows)
    ):
        raise ValueError(f"{name}: incomplete or duplicate pairing")
    rows = []
    for raw_id, r in ring_rows.items():
        u = under_rows[raw_id]
        if (
            r["source_prefix_class"] != u["source_prefix_class"]
            or r.get("sample_times_s", r.get("sample_source_times_s")) != u["sample_source_times_s"]
        ):
            raise ValueError(f"{name} {raw_id}: class or time differs")
        ring_score = r["median_nonice_ring_fraction"]
        under_score = u["median_underpoint_nonice_fraction"]
        tier = (
            "unavailable_review"
            if under_score is None
            else "cluttered_review"
            if ring_score > RING_THRESHOLD or under_score > UNDERPOINT_THRESHOLD
            else "clear_context_review"
        )
        rows.append(
            {
                "recording": name,
                "raw_track_id": raw_id,
                "source_prefix_class": source_class(r["source_prefix_class"]),
                "ring_nonice_fraction": ring_score,
                "underpoint_nonice_fraction": under_score,
                "combined_review_tier": tier,
            }
        )
    return {
        "recording": name,
        "ring_score_sha256": digest(ring_path),
        "underpoint_score_sha256": digest(underpoint_path),
        "rows": rows,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pair",
        nargs=3,
        action="append",
        metavar=("RECORDING", "RING_SCORE", "UNDERPOINT_SCORE"),
        required=True,
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    pairs = [join_pair(name, Path(ring), Path(under)) for name, ring, under in args.pair]
    names = [pair["recording"] for pair in pairs]
    if len(names) != len(set(names)):
        parser.error("Duplicate recording")
    rows = [row for pair in pairs for row in pair.pop("rows")]
    counts = Counter((row["source_prefix_class"], row["combined_review_tier"]) for row in rows)
    result = {
        "status": "exposed_development_short_prefix_diagnostic_not_event_accuracy",
        "ring_review_threshold": RING_THRESHOLD,
        "underpoint_review_threshold": UNDERPOINT_THRESHOLD,
        "pairs": pairs,
        "counts_by_source_class_and_tier": {
            cls: {
                tier: counts[cls, tier]
                for tier in ("clear_context_review", "cluttered_review", "unavailable_review")
            }
            for cls in sorted({row["source_prefix_class"] for row in rows})
        },
        "rows": rows,
        "limitations": [
            "The underpoint geometry and threshold were selected after viewing Slovakia head-track failures.",
            "All classes are same-agent source-visible prefixes, not physical throw truth.",
            "Selected prefixes do not provide an exhaustive delivery denominator.",
            "Clear context is a review cue, not an accepted stone or throw.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"rows": len(rows), "counts": result["counts_by_source_class_and_tier"]}))


if __name__ == "__main__":
    main()
