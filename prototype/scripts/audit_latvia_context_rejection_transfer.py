"""Join Latvia full-run context decisions to existing source-pixel reviews."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark"
RUN = BASE / "layout-router/full-2024-coverage/latvia24-full-v1/run-02"
RAW = RUN / "raw.json"
EVENTS = RUN / "events.json"
LEDGER = BASE / "canada-latvia-2024/full-match-area-censored-candidate-handoff-all-left-source-reviewed-development.json"
OUT = RUN.parent / "context-rejection-source-review-transfer-development.json"


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def review(row):
    source = row.get("source_pixel_review")
    if not source:
        raise ValueError(f"Missing source review: {row['candidate_id']}")
    image_path = source.get("image_path", source.get("sheet_path"))
    if image_path is None:
        raise ValueError(f"Source review lacks a frame reference: {row['candidate_id']}")
    candidates = [LEDGER.parent / image_path, RUN.parent / image_path]
    matches = [path for path in candidates if path.is_file()]
    if len(matches) != 1:
        raise ValueError(f"Review image not uniquely found: {image_path}")
    path = matches[0]
    return {"source_pixel_class": source["source_pixel_class"],
            "review_origin": source["review_origin"],
            "review_image_path": str(path.relative_to(BASE)),
            "review_image_sha256": digest(path),
            "physical_throw_verified": source["physical_throw_verified"]}


def main():
    if OUT.exists():
        raise ValueError("Latvia context transfer already exists")
    raw, events, ledger = (json.loads(path.read_text()) for path in
                           (RAW, EVENTS, LEDGER))
    if not (raw["source_sha256"] == events["source_sha256"] ==
            ledger["source_sha256"]):
        raise ValueError("Source hash mismatch")
    if (events["input_sha256"] != digest(RAW) or
            ledger["provenance"]["source_video_sha256"]["lowres"] !=
            raw["source_sha256"]):
        raise ValueError("Source or raw artifact lineage mismatch")
    raw_by_id = {row["id"]: row for row in raw["events"]}
    ledger_by_id = {row["candidate_id"].split("left:R01-")[-1]: row for row in
                    ledger["ordered_candidates"] if row["candidate_id"].startswith(
                        "left:R01-S")}
    if (len(raw_by_id) != len(raw["events"]) or
            len(ledger_by_id) != sum(row["candidate_id"].startswith("left:R01-S")
                                     for row in ledger["ordered_candidates"]) or
            set(ledger_by_id) != set(raw_by_id)):
        raise ValueError("Left candidate IDs differ or repeat")
    for id, raw_row in raw_by_id.items():
        old = ledger_by_id.get(id)
        if (old is None or old["source_time_s"] != raw_row["crossing_time_s"]
                or old["colour_claim"] != raw_row["colour"]):
            raise ValueError(f"Current and reviewed raw candidate differ: {id}")
    confirmed = {row["id"] for row in events["events"]}
    if confirmed != {id for id, row in ledger_by_id.items() if
                     row["evidence_tier"] ==
                     "left_screen_confirmed_not_physical_throw"}:
        raise ValueError("Confirmed candidate IDs differ from reviewed ledger")
    rejected = []
    for decision in events["decisions"]:
        if decision["reason"] != "large_surrounding_motion":
            continue
        id = decision["id"]
        if id in confirmed or decision["status"] != "unconfirmed":
            raise ValueError(f"Unexpected large-motion status: {id}")
        rejected.append({"candidate_id": id,
                         "passage_time_s": raw_by_id[id]["crossing_time_s"],
                         "changed_px_80x80": decision["changed_px_80x80"],
                         **review(ledger_by_id[id])})
    accepted_no_right = []
    for id in sorted(confirmed, key=lambda value: raw_by_id[value][
                     "crossing_time_s"]):
        old = ledger_by_id[id]
        if old.get("accepted_no_right_source_review") is None:
            continue
        accepted_no_right.append({"candidate_id": id,
                                  "passage_time_s": raw_by_id[id]["crossing_time_s"],
                                  **review(old)})
    OUT.write_text(json.dumps({
        "status": "development_transfer_of_context_rejections_and_right_absence_not_throw_labels",
        "source_sha256": raw["source_sha256"],
        "input_sha256": {"raw": digest(RAW), "events": digest(EVENTS),
                         "review_ledger": digest(LEDGER)},
        "runner_sha256": digest(Path(__file__)),
        "raw_candidate_count": len(raw_by_id),
        "context_confirmed_candidate_count": len(confirmed),
        "large_surrounding_motion_rejection_count": len(rejected),
        "large_motion_source_pixel_class_counts": dict(Counter(row[
            "source_pixel_class"] for row in rejected)),
        "accepted_no_right_review_count": len(accepted_no_right),
        "accepted_no_right_source_pixel_class_counts": dict(Counter(row[
            "source_pixel_class"] for row in accepted_no_right)),
        "large_motion_rejections": rejected,
        "accepted_without_right_proposal": accepted_no_right,
        "limitations": [
            "Source-pixel judgments were made by the same agent after proposal selection; they are not independent event labels.",
            "A person/equipment raw track does not prove no physical throw occurred nearby.",
            "No right proposal in the historical handoff is a missing observation, not a negative physical-event label.",
            "These image crops do not establish distinct deliveries, physical release times, or complete game state.",
        ],
    }, indent=2) + "\n")
    print(json.dumps({"large_motion_rejected": len(rejected),
                      "accepted_without_right": len(accepted_no_right)}))


if __name__ == "__main__":
    main()
