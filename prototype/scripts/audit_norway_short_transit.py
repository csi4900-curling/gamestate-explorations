"""Explore brief verified-cap transit in exposed end-2 broadcast windows."""

from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from short_cap_transit import short_transits

INPUT = (
    ROOT
    / "validation/curlobserver-learned-probe/cap-patch-crossmatch-v1/norway-end2-targeted-transfer.json"
)
OUTPUT = (
    ROOT
    / "validation/curlobserver-learned-probe/cap-patch-crossmatch-v1/norway-end2-short-transit.json"
)


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first short-transit diagnostic")
    source = json.loads(INPUT.read_text())
    rows = []
    for window in source["rows"]:
        transits = []
        for colour in ("red", "yellow"):
            observations = [
                (
                    sample["time_s"],
                    [
                        candidate
                        for candidate in sample["candidates"][colour]
                        if candidate["patch_accepted"]
                    ],
                )
                for sample in window["samples"]
            ]
            transits.extend(dict(track, colour=colour) for track in short_transits(observations))
        transits.sort(key=lambda row: (-row["point_count"], -row["displacement_px"]))
        rows.append(
            {
                "shot_id": window["shot_id"],
                "counter_proxy_colour": window["counter_proxy_colour"],
                "frozen_visual_colour": window["frozen_visual_colour"],
                "transits": transits,
                "top_transit_colour": transits[0]["colour"] if transits else None,
            }
        )
    result = {
        "status": "postscore_exposed_short_verified_cap_transit_not_event_f1",
        "source_sha256": source["source_sha256"],
        "input_sha256": digest(INPUT),
        "motion_code_sha256": digest(ROOT / "prototype/short_cap_transit.py"),
        "runner_sha256": digest(Path(__file__)),
        "rule": "Accepted broadcast cap patches, nearest local link at <=0.65 s and <=260 px/s; >=3 points, >=0.4 s, >=30 px chord, path/chord <=1.8; rank by point count then displacement.",
        "rows": rows,
        "limitations": [
            "This rule was designed after viewing these eight exposed windows; no held-out score is claimed.",
            "The patch verifier uses developer-labelled training samples, and the counter is a delayed proxy.",
            "Short local motion does not prove delivery origin, one-to-one identity, or a camera-handoff link.",
            "Other camera layouts, quiet periods, and the full recording have not been scanned by this rule.",
        ],
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    for row in rows:
        print(
            row["shot_id"],
            row["counter_proxy_colour"],
            row["top_transit_colour"],
            [(t["colour"], t["point_count"], t["displacement_px"]) for t in row["transits"]],
        )


if __name__ == "__main__":
    main()
