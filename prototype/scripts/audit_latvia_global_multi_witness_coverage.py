"""Measure multi-episode timing coverage on the existing 19 source witnesses."""

from hashlib import sha256
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark/canada-latvia-2024"
WITNESSES = BASE / "full-right-source-stone-witness-coverage-development.json"
GLOBAL = BASE / "full-right-global-area-development.json"
MULTI = BASE / "full-right-global-multi-episode-development.json"
SOURCE_AUDIT = BASE / "full-right-global-later-episode-source-audit.json"
OUT = BASE / "full-right-global-multi-witness-coverage-development.json"
WINDOW_S = 8


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def main():
    if OUT.exists():
        raise ValueError("Multi-episode witness coverage already exists")
    witnesses, global_scan, multi, audit = [
        json.loads(path.read_text()) for path in (WITNESSES, GLOBAL, MULTI, SOURCE_AUDIT)
    ]
    if (
        not witnesses["source_video_sha256"]
        == global_scan["source_sha256"]
        == multi["source_sha256"]
        == audit["source_video_sha256"]
        or multi["global_scan_sha256"] != digest(GLOBAL)
        or audit["input_sha256"]["multi_episode_probe"] != digest(MULTI)
        or witnesses["witness_count"] != 19
    ):
        raise ValueError("Multi-episode witness input lineage differs")
    later = multi["later_review_proposals"]
    rows = []
    for witness in witnesses["witnesses"]:
        baseline = witness["scan_temporal_matches"]["two_second_global"]
        extra = [
            row
            for row in later
            if row["colour_claim"] == witness["colour_claim"]
            and row["direction"] == witness["direction"]
            and abs(row["passage"]["time_s"] - witness["source_time_s"]) <= WINDOW_S
        ]
        rows.append(
            {
                "witness_id": witness["witness_id"],
                "baseline_global_temporal_matches": baseline,
                "later_episode_temporal_matches": [
                    {
                        "raw_track_id": row["raw_track_id"],
                        "episode_index_within_raw_track": row["episode_index_within_raw_track"],
                        "passage_time_s": row["passage"]["time_s"],
                    }
                    for row in extra
                ],
                "any_temporal_proposal": bool(baseline or extra),
            }
        )
    covered = sum(row["any_temporal_proposal"] for row in rows)
    added = [
        row["witness_id"]
        for row in rows
        if not row["baseline_global_temporal_matches"] and row["later_episode_temporal_matches"]
    ]
    if covered != 19 or added != ["end6:A452"]:
        raise ValueError("Multi-episode witness coverage differs")
    result = {
        "status": "development_multi_episode_stone_pixel_timing_coverage_not_event_recall",
        "source_video_sha256": witnesses["source_video_sha256"],
        "input_sha256": {
            "source_witnesses": digest(WITNESSES),
            "global_scan": digest(GLOBAL),
            "multi_episode_probe": digest(MULTI),
            "later_episode_source_audit": digest(SOURCE_AUDIT),
        },
        "runner_sha256": digest(Path(__file__)),
        "temporal_match_window_s": WINDOW_S,
        "witness_count": len(rows),
        "baseline_global_witnesses_with_temporal_proposal": witnesses["coverage"][
            "two_second_global"
        ]["witnesses_with_temporal_proposal"],
        "multi_episode_witnesses_with_temporal_proposal": covered,
        "witness_ids_restored_by_later_episode": added,
        "baseline_global_proposals": global_scan["directional_proposal_count"],
        "multi_episode_proposals": multi["all_review_proposal_count"],
        "later_source_class_counts": audit["source_class_counts"],
        "rows": rows,
        "limitations": [
            "Witnesses are same-agent postproposal stone-pixel reviews, not an exhaustive independent throw reference.",
            "A temporal proposal with matching colour/direction does not prove same-stone identity or physical release.",
            "Three of four later spans have mixed object pixels in source frames, so coverage gain is not an automatic event gain.",
            "No physical-event F1, complete board or simulation readiness is inferred.",
        ],
    }
    OUT.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"witnesses_covered": covered, "witness_count": len(rows), "restored": added}))


if __name__ == "__main__":
    main()
