"""Render EVERY emitted projected sample; no cherry-picked trajectory frames."""

import argparse
import json
from pathlib import Path
import sys
import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256


def render(video, aggregate, output, reviewed=(), columns=6, page_rows=4):
    page_size = columns * page_rows
    if columns < 1 or page_rows < 1:
        raise ValueError("Invalid review grid")
    data = json.loads(aggregate.read_text())
    if file_sha256(video) != data["context"]["source_sha256"]:
        raise ValueError("Source mismatch")
    known = set()
    for path in reviewed:
        labels = json.loads(path.read_text())
        if labels["source_sha256"] != data["context"]["source_sha256"]:
            continue
        for row in labels["rows"]:
            if type(row.get("correct_stone_at_pixel")) is bool:
                known.add((row["candidate_id"], row["time_s"], tuple(row["pixel"])))
    output.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(video))
    rows = []
    tiles = []
    for event in data["events"]:
        for segment in event["segments"]:
            for point in segment["geometry_samples"]:
                if point["top_view_m"] is None:
                    continue
                if (event["candidate_id"], point["time_s"], tuple(point["pixel"])) in known:
                    continue
                cap.set(cv2.CAP_PROP_POS_MSEC, point["time_s"] * 1000)
                ok, frame = cap.read()
                if not ok:
                    raise ValueError("Decode failed")
                frame = cv2.resize(frame, (640, 360))
                x, y = point["pixel"]
                crop = cv2.getRectSubPix(frame, (64, 48), (float(x), float(y)))
                tile = np.full((166, 192, 3), 245, np.uint8)
                tile[22:] = cv2.resize(crop, (192, 144), interpolation=cv2.INTER_NEAREST)
                label = f"{len(rows)} {event['candidate_id']} {point['time_s']:.1f}"
                cv2.putText(tile, label, (2, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 0), 1)
                rows.append(
                    {
                        "index": len(rows),
                        "candidate_id": event["candidate_id"],
                        "segment_id": segment["segment_id"],
                        "camera": segment["camera"],
                        "time_s": point["time_s"],
                        "pixel": point["pixel"],
                        "sheet": f"points-{len(rows) // page_size:03}.jpg",
                        "correct_stone_at_pixel": None,
                    }
                )
                tiles.append(tile)
                if len(tiles) == page_size:
                    cv2.imwrite(
                        str(output / f"points-{(len(rows) - 1) // page_size:03}.jpg"),
                        np.vstack(
                            [
                                np.hstack(tiles[i : i + columns])
                                for i in range(0, page_size, columns)
                            ]
                        ),
                    )
                    tiles = []
    if tiles:
        tiles += [np.full_like(tiles[0], 245)] * ((-len(tiles)) % columns)
        cv2.imwrite(
            str(output / f"points-{(len(rows) - 1) // page_size:03}.jpg"),
            np.vstack([np.hstack(tiles[i : i + columns]) for i in range(0, len(tiles), columns)]),
        )
    cap.release()
    (output / "manifest.json").write_text(
        json.dumps(
            {
                "source_sha256": file_sha256(video),
                "aggregate_sha256": file_sha256(aggregate),
                "rows": rows,
                "scope": "Every emitted projected sample, prediction-centred source crop; object identity requires annotation. Physical geometry is separate.",
            },
            indent=2,
        )
        + "\n"
    )
    print(f"{len(rows)} projected source samples")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--video", type=Path, required=True)
    p.add_argument("--aggregate", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--reviewed", type=Path, action="append", default=[])
    p.add_argument("--columns", type=int, default=6)
    p.add_argument("--page-rows", type=int, default=4)
    a = p.parse_args()
    render(a.video, a.aggregate, a.output, a.reviewed, a.columns, a.page_rows)
