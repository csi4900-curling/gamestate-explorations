"""Compare right proposal timing coverage on 19 source-reviewed stone paths."""

from hashlib import sha256
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark/canada-latvia-2024"
VIDEO = BASE / "source-360p.mp4"
CLASSES = BASE / "full-right-area-end6-right-only-source-review/source-prefix-classes.json"
END1 = BASE / "end1-omitted-right-area-source-audit/manifest.json"
END5 = BASE / "end5-omitted-right-area-source-audit/manifest.json"
R008 = BASE / "r008-area-gap2-split-audit.json"
LEDGER = BASE / "full-match-area-censored-candidate-handoff-r008-source-reviewed-development.json"
SCANS = {
    "one_second_greedy": BASE / "full-right-area-first-transfer.json",
    "two_second_greedy": BASE / "full-right-area-gap2-development.json",
    "two_second_global": BASE / "full-right-global-area-development.json",
}
OUT = BASE / "full-right-source-stone-witness-coverage-development.json"
WINDOW_S = 8


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def matching_proposals(witness, proposals):
    return [row for row in proposals if
            row["colour_claim"] == witness["colour_claim"] and
            row["direction"] == witness["direction"] and
            abs(row["passage"]["time_s"] - witness["source_time_s"]) <= WINDOW_S]


def main():
    if OUT.exists():
        raise ValueError("Right witness coverage audit already exists")
    classes = json.loads(CLASSES.read_text())
    end1, end5, r008, ledger = [json.loads(path.read_text()) for path in
                                 (END1, END5, R008, LEDGER)]
    scans = {name: json.loads(path.read_text()) for name, path in SCANS.items()}
    source_hash = digest(VIDEO)
    if not (classes["source_sha256"] == end1["source_video_sha256"] == end5[
            "source_video_sha256"] == r008["source_video_sha256"] == ledger[
            "source_sha256"] == source_hash) or any(scan["source_sha256"] !=
            source_hash for scan in scans.values()):
        raise ValueError("Stone witness/source fingerprint differs")
    baseline = scans["one_second_greedy"]
    baseline_by_id = {row["raw_track_id"]: row for row in baseline[
        "directional_review_proposals"]}
    reviewed_end6 = [row["right_proposal_id"].removeprefix("R01:")
                     for row in classes["rows"] if row[
                         "sampled_prefix_class"] == "moving_stone_pixels"]
    if len(reviewed_end6) != 16 or len(set(reviewed_end6)) != 16:
        raise ValueError("End-six source-reviewed stone path inventory differs")
    witnesses = []
    for track_id in reviewed_end6:
        proposal = baseline_by_id[track_id]
        witnesses.append({
            "witness_id": "end6:" + track_id,
            "source_time_s": proposal["passage"]["time_s"],
            "colour_claim": proposal["colour_claim"],
            "direction": proposal["direction"],
            "source_pixel_class": "moving_stone_pixels",
            "review_origin": "same_agent_baseline_proposal_source_review",
        })
    for name, audit in (("end1:A008", end1), ("end5:A367", end5)):
        if audit["source_pixel_class"] != "moving_red_stone_body_pixels":
            raise ValueError(f"Right gap source class differs: {name}")
        witnesses.append({
            "witness_id": name,
            "source_time_s": audit["source_time_s"],
            "colour_claim": audit["colour_claim"],
            "direction": audit["direction"],
            "source_pixel_class": audit["source_pixel_class"],
            "review_origin": audit["class_origin"],
        })
    old = [row for row in ledger["ordered_candidates"] if row[
        "candidate_id"] == "right:R008"]
    if (len(old) != 1 or old[0]["source_pixel_review"]["source_pixel_class"] !=
            "moving_red_stone_body_pixels" or r008["candidate_id"] !=
            "right:R008"):
        raise ValueError("R008 source-reviewed witness differs")
    witnesses.append({
        "witness_id": "older_right:R008",
        "source_time_s": old[0]["source_time_s"],
        "colour_claim": "red",
        "direction": "negative_y",
        "source_pixel_class": "moving_red_stone_body_pixels",
        "review_origin": r008["source_class_origin"],
    })
    witnesses.sort(key=lambda row: row["source_time_s"])
    if len(witnesses) != 19:
        raise ValueError("Source-reviewed right stone witness count differs")
    for witness in witnesses:
        witness["scan_temporal_matches"] = {}
        for name, scan in scans.items():
            matched = matching_proposals(witness,
                                         scan["directional_review_proposals"])
            witness["scan_temporal_matches"][name] = [{
                "raw_track_id": row["raw_track_id"],
                "passage_time_s": row["passage"]["time_s"],
                "time_difference_s": row["passage"]["time_s"] - witness[
                    "source_time_s"],
            } for row in matched]
    coverage = {name: {
        "witnesses_with_temporal_proposal": sum(bool(row[
            "scan_temporal_matches"][name]) for row in witnesses),
        "witnesses_without_temporal_proposal": [row["witness_id"]
            for row in witnesses if not row["scan_temporal_matches"][name]],
    } for name in scans}
    output = {
        "status": "development_source_reviewed_stone_pixel_timing_coverage_not_event_recall",
        "source_video_sha256": source_hash,
        "input_sha256": {
            "end6_source_classes": digest(CLASSES),
            "end1_source_audit": digest(END1),
            "end5_source_audit": digest(END5),
            "r008_split_audit": digest(R008),
            "r008_reviewed_ledger": digest(LEDGER),
            "scans": {name: digest(path) for name, path in SCANS.items()},
        },
        "runner_sha256": digest(Path(__file__)),
        "temporal_match_rule": "same claimed colour, same image direction, passage time within 8 seconds",
        "window_s": WINDOW_S,
        "witness_count": len(witnesses),
        "coverage": coverage,
        "witnesses": witnesses,
        "limitations": [
            "Witnesses were selected or reviewed after detector proposals by the same agent and are not an independent exhaustive event reference.",
            "A nearby proposal is a timing/colour/direction association, not proven same-stone identity.",
            "The 16 end-six witnesses come from the baseline scan, so comparison favors its existing proposal inventory.",
            "Stone pixels do not certify a distinct physical delivery, full trajectory or settled board.",
            "Counts are source-visible proposal coverage diagnostics, not physical-event precision, recall or F1.",
        ],
    }
    OUT.write_text(json.dumps(output, indent=2, allow_nan=False) + "\n")
    print(json.dumps(coverage))


if __name__ == "__main__":
    main()
