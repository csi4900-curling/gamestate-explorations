"""Runtime diagnostics and an explicitly reused development-frame sanity check."""

from pathlib import Path
import json, math, collections

root = Path(__file__).resolve().parents[1]
d = json.loads((root / "continuous/timeline.json").read_text())
refs = json.loads((root / "vision/annotations/detection-reference.json").read_text())
assert d["decoded_frames"] > 2600 and len(d["records"]) == 180
out = {
    "samples": len(d["records"]),
    "duration_s": d["duration_s"],
    "views": {},
    "reused_development_frame_check": [],
    "note": "Diagnostics, not independent accuracy evaluation. Full passage has no ground-truth tracking labels.",
}
for name in ["left", "right"]:
    views = [r["views"][name] for r in d["records"]]
    stones = [s for v in views for s in v["stones"]]
    out["views"][name] = {
        "registration_statuses": dict(
            collections.Counter(v["registration"]["status"] for v in views)
        ),
        "detection_observations": len(stones),
        "distinct_provisional_ids": len({s["track_id"] for s in stones}),
        "persistent_observations": sum(s["track_status"] == "persistent" for s in stones),
        "stable_observations": sum(s["motion_status"] == "visually_stable" for s in stones),
    }
for ref in refs["frames"]:
    if ref["timestamp_s"] != 2300:
        continue
    row = min(d["records"], key=lambda r: abs(r["source_time_s"] - 2300))
    pred = row["views"][ref["panel"]]["stones"]
    pairs = []
    for i, p in enumerate(pred):
        for j, (x, y, c) in enumerate(ref["caps"]):
            dist = math.dist(p["pixel_center"], [x, y])
            if p["colour"] == c and dist <= 20:
                pairs.append((dist, i, j))
    usedp = set()
    usedr = set()
    for dist, i, j in sorted(pairs):
        if i not in usedp and j not in usedr:
            usedp.add(i)
            usedr.add(j)
    out["reused_development_frame_check"].append(
        {
            "panel": ref["panel"],
            "source_time_s": row["source_time_s"],
            "tp": len(usedp),
            "fp": len(pred) - len(usedp),
            "fn": len(ref["caps"]) - len(usedr),
        }
    )
(root / "continuous/diagnostics.json").write_text(json.dumps(out, indent=2))
print(json.dumps(out, indent=2))
