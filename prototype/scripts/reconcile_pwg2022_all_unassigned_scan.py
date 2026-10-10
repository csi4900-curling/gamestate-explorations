"""Verify the full unassigned-shot scan and compare frozen origin-positive rows."""

from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/official-shot-sequence"
PLAN = BASE / "pwg2022-all-unassigned-shots-source-scan-plan.json"
UNION = BASE / "pwg2022-provisional-event-evidence-union-v2-source-rescues-development.json"
EARLIER = BASE / "pwg2022-origin-shots-outside-union-cues-development.json"
SCANS = {code: BASE / f"pwg2022-all-unassigned-shots-{code}-source-scan-development.json"
         for code in ("PREL000101", "PREL000102", "PREL000103")}
OUTPUT = BASE / "pwg2022-all-unassigned-shots-source-scan-summary-development.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def build():
    plan = json.loads(PLAN.read_text())
    union = json.loads(UNION.read_text())
    earlier = json.loads(EARLIER.read_text())
    if plan["union_sha256"] != digest(UNION):
        raise ValueError("Frozen selection and v2 union differ")
    old_by_code = {game["recording_code"]: {row["shot_id"]: row
                   for row in game["rows"]} for game in earlier["games"]}
    union_by_code = {game["official_game_code"]: game for game in union["games"]}
    games = []
    for selected in plan["games"]:
        code = selected["recording_code"]
        path = SCANS[code]
        scan = json.loads(path.read_text())
        if (scan["plan_sha256"] != digest(PLAN) or
                scan["source_sha256"] != selected["source_sha256"] or
                scan["scanned_shot_count"] != selected["unassigned_shot_count"] or
                [{k: row[k] for k in ("shot_id", "interval_s",
                                           "origin_model_predicted", "origin_probability")}
                 for row in scan["rows"]] != selected["selected_shots"]):
            raise ValueError(f"Full scan does not match frozen shot selection: {code}")
        used = {sid for event in union_by_code[code]["events"]
                for sid in event["source_shot_ids"]}
        if any(row["shot_id"] in used for row in scan["rows"]):
            raise ValueError("Scan contains an assigned v2 event camera shot")
        compared = 0
        for row in scan["rows"]:
            old = old_by_code[code].get(row["shot_id"])
            if old is None:
                continue
            for key in ("interval_s", "sampled_frame_count",
                        "filtered_cap_observation_count", "raw_passages",
                        "ice_supported_passages", "ice_rejected_passages"):
                if row[key] != old[key]:
                    raise ValueError(f"Frozen positive-shot scan changed: {code}/{row['shot_id']}/{key}")
            compared += 1
        candidates = [{"shot_id": row["shot_id"], "interval_s": row["interval_s"],
                       "origin_model_predicted": row["origin_model_predicted"],
                       "origin_probability": row["origin_probability"],
                       "passages": row["ice_supported_passages"]}
                      for row in scan["rows"]
                      if row["unique_ice_supported_colour"] is not None]
        games.append({"recording_code": code, "source_sha256": selected["source_sha256"],
                      "scan_sha256": digest(path),
                      "scanned_shot_count": scan["scanned_shot_count"],
                      "origin_predicted_shot_count": scan["origin_predicted_shot_count"],
                      "earlier_positive_shots_reproduced": compared,
                      "raw_passage_shot_count": scan["raw_passage_shot_count"],
                      "unique_ice_supported_shot_count": scan[
                          "unique_ice_supported_shot_count"],
                      "model_negative_unique_ice_supported_shot_count": sum(
                          not row["origin_model_predicted"] for row in candidates),
                      "candidates": candidates})
    if sum(g["scanned_shot_count"] for g in games) != plan[
            "total_unassigned_shot_count"]:
        raise ValueError("Incomplete full unassigned-shot scan")
    return {"status": "development_full_unassigned_shot_scan_summary_not_physical_event_f1",
            "input_sha256": {"plan": digest(PLAN), "union_v2": digest(UNION),
                             "earlier_origin_positive_scan": digest(EARLIER),
                             "runner": digest(Path(__file__))},
            "scanned_shot_count": sum(g["scanned_shot_count"] for g in games),
            "raw_passage_shot_count": sum(g["raw_passage_shot_count"] for g in games),
            "unique_ice_supported_shot_count": sum(
                g["unique_ice_supported_shot_count"] for g in games),
            "model_negative_unique_ice_supported_shot_count": sum(
                g["model_negative_unique_ice_supported_shot_count"] for g in games),
            "games": games,
            "limitations": [
                "Unassigned camera shots are not independently labeled negative examples; cues may be missed physical throws or duplicates.",
                "The held-to-motion rule is source geometry dependent and can miss throws even after this complete shot scan.",
                "No automatic promotion, physical stone identity, or full-video event precision/recall follows from these counts.",
            ]}


def main():
    payload = json.dumps(build(), indent=2) + "\n"
    if OUTPUT.exists() and OUTPUT.read_text() != payload:
        raise SystemExit("Existing full-scan summary differs from hashed inputs")
    if not OUTPUT.exists():
        OUTPUT.write_text(payload)
    print(f"Verified {OUTPUT}")


if __name__ == "__main__":
    main()
