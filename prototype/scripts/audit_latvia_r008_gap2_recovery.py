"""Explain the exact R008 split and local gap-two reconnection."""

from hashlib import sha256
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark/canada-latvia-2024"
SOURCE_REVIEW = (
    ROOT / "validation/throw-event-benchmark/layout-router/full-2024-coverage/"
    "latvia24-full-v1/right-entry-review/manifest.json"
)
LEDGER = (
    BASE
    / "full-match-area-censored-candidate-handoff-all-area-right-only-accounted-development.json"
)
AREA = BASE / "full-right-area-first-transfer.json"
GAP2 = BASE / "right-area-gap2-r008-5080-5140-development.json"
GLOBAL = BASE / "right-global-r008-5080-5140-development.json"
VIDEO = BASE / "source-360p.mp4"
OUT = BASE / "r008-area-gap2-split-audit.json"


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def local_path(scan):
    proposals = [
        row
        for row in scan["directional_review_proposals"]
        if row["colour_claim"] == "red"
        and row["direction"] == "negative_y"
        and 5115 <= row["passage"]["time_s"] <= 5122
    ]
    if len(proposals) != 1:
        raise ValueError("Local R008 recovery is not unique")
    proposal = proposals[0]
    track = next(row for row in scan["raw_tracks"] if row["track_id"] == proposal["raw_track_id"])
    return proposal, track


def main():
    if OUT.exists():
        raise ValueError("R008 audit already exists")
    ledger, area, gap2, global_scan, review = [
        json.loads(path.read_text()) for path in (LEDGER, AREA, GAP2, GLOBAL, SOURCE_REVIEW)
    ]
    source_hash = digest(VIDEO)
    if not (
        ledger["source_sha256"]
        == area["source_sha256"]
        == gap2["source_sha256"]
        == global_scan["source_sha256"]
        == review["source_sha256"]
        == source_hash
    ):
        raise ValueError("R008 source video fingerprints differ")
    if (
        not gap2["source_interval_s"] == global_scan["source_interval_s"] == [5080, 5140]
        or gap2["maximum_inter_sample_gap_s"] != 2
        or global_scan["maximum_inter_sample_gap_s"] != 2
        or not area["sample_period_s"] == gap2["sample_period_s"] == 1
    ):
        raise ValueError("R008 local comparison settings differ")
    old = [row for row in ledger["ordered_candidates"] if row["candidate_id"] == "right:R008"]
    if len(old) != 1 or old[0]["source_pixel_review"] is not None:
        raise ValueError("Older R008 candidate differs")
    prefix = old[0]["observed_motion"]["observed_prefix_points"]
    split = [
        point
        for track in area["raw_tracks"]
        if track["track_id"] in ("A352", "A353")
        for point in track["points"]
        if 5115 <= point["time_s"] <= 5121
    ]
    split.sort(key=lambda point: point["time_s"])
    if len(prefix) != 6 or prefix != split:
        raise ValueError("Frozen area tracks do not reproduce older R008 prefix")
    recovered = {}
    for kind, scan in (("area_gap2", gap2), ("global_gap2", global_scan)):
        proposal, track = local_path(scan)
        observed = [
            point
            for point in track["points"]
            if point["time_s"] in {row["time_s"] for row in prefix}
        ]
        if (
            observed != prefix
            or proposal["passage"]["time_s"] < 5115
            or proposal["passage"]["time_s"] > 5122
        ):
            raise ValueError(f"{kind} does not reconnect exact R008 prefix")
        recovered[kind] = {
            "raw_track_id_local_interval": track["track_id"],
            "passage_time_s": proposal["passage"]["time_s"],
            "passage_time_semantics": proposal["passage_kind"],
            "prefix_points_exactly_match_old_candidate": True,
            "reconnected_observation_count": len(observed),
            "full_track_observation_count": len(track["points"]),
        }
    source_sheet = SOURCE_REVIEW.parent / "sheet-01.jpg"
    sheet = next(row for row in review["sheets"] if row["file"] == source_sheet.name)
    if sheet["sha256"] != digest(source_sheet) or "R008" not in sheet["track_ids"]:
        raise ValueError("Archived R008 source review differs")
    output = {
        "status": "postinspection_r008_exact_observation_recovery_not_event_recall",
        "source_video_sha256": source_hash,
        "input_sha256": {
            "previous_ledger": digest(LEDGER),
            "one_second_gap_area_scan": digest(AREA),
            "local_area_gap2_scan": digest(GAP2),
            "local_global_gap2_scan": digest(GLOBAL),
            "archived_source_review": digest(SOURCE_REVIEW),
            "archived_source_sheet": digest(source_sheet),
        },
        "runner_sha256": digest(Path(__file__)),
        "archived_source_sheet_path": str(source_sheet.relative_to(ROOT)),
        "candidate_id": "right:R008",
        "source_pixel_class": "moving_red_stone_body_pixels",
        "source_class_origin": "same_agent_archived_source_sheet_reinspection",
        "old_prefix_interval_s": old[0]["observed_motion"]["observed_prefix_interval_s"],
        "one_second_gap_area_raw_track_ids": ["A352", "A353"],
        "old_prefix_equals_combined_split_raw_points": True,
        "local_gap2_recoveries": recovered,
        "physical_throw_verified": False,
        "limitations": [
            "This source-visible stone-body path is not an independently labelled physical delivery.",
            "The local 5080–5140 s replay was chosen after the full-source one-second scan miss was known.",
            "Exact prefix equality proves data association on saved observations, not continuous physical identity after the prefix.",
            "Full-source proposal side effects must be audited before replacing the one-second scan.",
        ],
    }
    OUT.write_text(json.dumps(output, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {"candidate_id": output["candidate_id"], "exactly_recovered_by": list(recovered)}
        )
    )


if __name__ == "__main__":
    main()
