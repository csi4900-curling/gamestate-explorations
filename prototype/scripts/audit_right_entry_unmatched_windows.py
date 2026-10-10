"""Compare fixed right-entry proposals and raw-track starts with coarse windows."""

import argparse
from hashlib import sha256
import json
from pathlib import Path


def digest(path):
    h = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--transfer", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    transfer = json.loads(args.transfer.read_text())
    reference = json.loads(args.reference.read_text())
    if transfer["source_sha256"] != reference["source_sha256"]:
        parser.error("Source fingerprints differ")
    rows = []
    for event in reference["events"]:
        lo, hi = event["delivery_interval_s"]
        colour = event["colour"]
        matches = [row for row in transfer["entry_review_proposals"]
                   if row["colour_claim"] == colour and
                   lo <= row["entry_crossing"]["time_s"] <= hi]
        if matches:
            continue
        starts = []
        for track in transfer["raw_tracks"]:
            if track["colour"] != colour or not lo <= track["first_observed_s"] <= hi:
                continue
            first = track["points"][0]
            starts.append({
                "track_id": track["track_id"],
                "first_observed_s": track["first_observed_s"],
                "first_y_px": first["pixel"][1],
                "first_cap_area_px2": first["cap_area_px2"],
                "first_bbox_width_height_px": first["bbox"][2:4],
                "last_observed_s": track["last_observed_s"],
                "min_y_in_first_20s_px": min(p["pixel"][1] for p in track["points"]
                                               if p["time_s"] <= first["time_s"] + 20),
            })
        rows.append({"reference_id": event["id"], "colour": colour,
                     "coarse_window_s": [lo, hi], "new_raw_track_starts": starts,
                     "no_new_same_colour_raw_track_in_window": not starts,
                     "all_new_raw_starts_above_y250": bool(starts) and
                     all(row["first_y_px"] < 250 for row in starts)})
    result = {
        "status": "postreview_raw_track_start_diagnostic_not_false_negative_labels",
        "source_sha256": transfer["source_sha256"],
        "transfer_sha256": digest(args.transfer),
        "reference_sha256": digest(args.reference),
        "runner_sha256": digest(Path(__file__)),
        "unmatched_window_count": len(rows),
        "no_new_same_colour_raw_track_count": sum(row["no_new_same_colour_raw_track_in_window"] for row in rows),
        "all_new_raw_starts_above_y250_count": sum(row["all_new_raw_starts_above_y250"] for row in rows),
        "unmatched_windows": rows,
        "limitations": [
            "A raw colour track is not physically identified as the delivered stone.",
            "Raw tracks that started before the coarse window are omitted from the start diagnostic.",
            "The coarse windows are same-agent development references and are not exhaustive truth.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"unmatched": len(rows),
                      "no_new_raw_start": result["no_new_same_colour_raw_track_count"],
                      "all_new_starts_above_y250": result["all_new_raw_starts_above_y250_count"]}))


if __name__ == "__main__":
    main()
