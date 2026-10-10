"""Audit same-time spatial continuity from raw proposals to left-view paths."""

from hashlib import sha256
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark"
RAW = BASE / "layout-router/czech24-full-camera-motion-v1/run-02/raw.json"
MOTION = BASE / "canada-czech-2024/full-match-motion-merged-postscore.json"
OUT = BASE / "layout-router/czech24-full-camera-motion-v1/raw-to-downstream-left-anchor-audit.json"


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def main():
    if OUT.exists():
        raise ValueError("Anchor audit exists")
    raw, motion = (json.loads(p.read_text()) for p in (RAW, MOTION))
    if (raw["source_sha256"] != motion["candidate_source_sha256"] or
            motion["source_offset_s"] != 0):
        raise ValueError("Raw and downstream motion lineage differs")
    by_id = {r["candidate_id"]: r for r in motion["rows"]}
    if len(by_id) != len(motion["rows"]) or not set(by_id) <= {
            e["id"] for e in raw["events"]}:
        raise ValueError("Candidate IDs do not match")
    rows = []
    for event in raw["events"]:
        downstream = by_id.get(event["id"])
        if downstream is None:
            continue
        if downstream["receiving_view"] != "left":
            continue
        selected = downstream["selection"]
        path = selected.get("path") or selected.get("shared_prefix", [])
        pairings = []
        for original in event["observed_track_points"]:
            for later in path:
                dt = abs(original["time_s"] - later["source_time_s"])
                if dt > 0.15:
                    continue
                source_1080 = [3 * v for v in original["pixel"]]
                pairings.append({
                    "raw_time_s": original["time_s"],
                    "downstream_time_s": later["source_time_s"],
                    "time_difference_s": round(dt, 3),
                    "raw_center_1080p_px": source_1080,
                    "downstream_center_1080p_px": later["pixel_center"],
                    "center_separation_px": round(math.dist(
                        source_1080, later["pixel_center"]), 3),
                })
        closest = min(pairings, key=lambda r: (
            r["time_difference_s"], r["center_separation_px"])) if pairings else None
        rows.append({"candidate_id": event["id"],
                     "downstream_selection_status": selected["status"],
                     "downstream_path_points": len(path),
                     "near_time_pair_count": len(pairings),
                     "closest_time_pair": closest})
    overlaps = [r for r in rows if r["closest_time_pair"] is not None]
    output = {
        "status": "raw_to_downstream_spatial_anchor_audit_not_identity_truth",
        "source_360p_sha256": raw["source_sha256"],
        "source_1080p_sha256": motion["high_resolution_source_sha256"],
        "input_sha256": {"raw": digest(RAW), "downstream_motion": digest(MOTION)},
        "runner_sha256": digest(Path(__file__)),
        "temporal_tolerance_s": 0.15,
        "raw_pixel_to_1080p_scale": 3,
        "left_view_rows": len(rows),
        "rows_with_near_time_pairs": len(overlaps),
        "rows": rows,
        "limitations": [
            "A spatial mismatch at matched source times refutes that pair as a local continuation; it does not identify the physical object in either track.",
            "Most downstream left paths begin after raw proposal confirmation, so absence of near-time pairs cannot verify or refute identity.",
            "This audit compares only same-view left paths; right-view paths require a calibrated cross-view correspondence.",
        ],
    }
    OUT.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({"left_view_rows": len(rows),
                      "near_time_pairs": len(overlaps),
                      "S96": next(r for r in rows if r["candidate_id"] == "S96")}))


if __name__ == "__main__":
    main()
