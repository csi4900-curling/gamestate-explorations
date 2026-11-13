"""Render every unmatched periodic cap comparison for source review."""

from hashlib import sha256
import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark"
VIDEO = BASE / "canada-latvia-2024/source-360p.mp4"
INPUT = (
    BASE
    / "layout-router/full-2024-coverage/latvia24-full-v1/end6-periodic-right-board-development.json"
)
OUT = BASE / "layout-router/full-2024-coverage/latvia24-full-v1"


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def render_panel(capture, fps, row, unmatched):
    time_s = row["anchor_time_s"] + 2
    capture.set(cv2.CAP_PROP_POS_FRAMES, round(time_s * fps))
    ok, frame = capture.read()
    if not ok:
        raise RuntimeError(f"Could not decode {time_s}")
    crop = frame[:, 320:].copy()
    for cap in row["stable_cap_proposals"]:
        x, y = (round(v) for v in cap["pixel_center"])
        highlight = cap["local_observation_id"] in unmatched
        cv2.circle(
            crop,
            (x - 320, y),
            8 if highlight else 5,
            (255, 0, 255) if highlight else (0, 180, 0),
            2,
        )
    panel = np.full((390, 320, 3), 255, dtype=np.uint8)
    panel[30:] = crop
    cv2.putText(
        panel,
        f"{time_s}s  unmatched {len(unmatched)}",
        (4, 21),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (0, 0, 0),
        1,
    )
    return panel


def main():
    data = json.loads(INPUT.read_text())
    if data["source_sha256"] != digest(VIDEO):
        raise ValueError("Source fingerprint differs")
    windows = {row["anchor_time_s"]: row for row in data["windows"]}
    changes = [
        row
        for row in data["adjacent_transitions"]
        if row["status"] == "conditional_image_cap_comparison"
        and (row["before_only_local_cap_ids"] or row["after_only_local_cap_ids"])
    ]
    if len(changes) != 15:
        raise ValueError("Unmatched comparison inventory changed")
    capture = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    fps = capture.get(cv2.CAP_PROP_FPS)
    rendered = []
    for item in changes:
        before = windows[item["before_anchor_s"]]
        after = windows[item["after_anchor_s"]]
        rendered.append(
            {
                "before_anchor_s": before["anchor_time_s"],
                "after_anchor_s": after["anchor_time_s"],
                "before_only_local_cap_ids": item["before_only_local_cap_ids"],
                "after_only_local_cap_ids": item["after_only_local_cap_ids"],
                "panel": np.hstack(
                    [
                        render_panel(capture, fps, before, set(item["before_only_local_cap_ids"])),
                        render_panel(capture, fps, after, set(item["after_only_local_cap_ids"])),
                    ]
                ),
            }
        )
    capture.release()
    files = []
    blank = np.full_like(rendered[0]["panel"], 255)
    for sheet_index, first in enumerate(range(0, len(rendered), 6), 1):
        group = rendered[first : first + 6]
        panels = [row["panel"] for row in group]
        while len(panels) < 6:
            panels.append(blank)
        sheet = np.vstack([np.hstack(panels[index : index + 2]) for index in (0, 2, 4)])
        path = OUT / f"end6-all-cap-changes-{sheet_index:02d}.jpg"
        if not cv2.imwrite(str(path), sheet):
            raise RuntimeError(f"Could not write {path}")
        files.append(
            {
                "path": str(path.relative_to(ROOT)),
                "sha256": digest(path),
                "anchor_pairs_s": [
                    [row["before_anchor_s"], row["after_anchor_s"]] for row in group
                ],
            }
        )
    result = {
        "status": "prediction_exposed_all_unmatched_source_frames_not_state_labels",
        "source_sha256": data["source_sha256"],
        "observations_sha256": digest(INPUT),
        "runner_sha256": digest(Path(__file__)),
        "pair_count": len(changes),
        "files": files,
        "same_agent_sampled_pair_review": [
            {
                "anchor_pair_s": [row["before_anchor_s"], row["after_anchor_s"]],
                "conclusion": "sampled_frames_do_not_verify_delivered_stone_or_board_transition",
                "physical_throw_verified": False,
                "physical_board_transition_verified": False,
                "independent_validation": False,
            }
            for row in rendered
        ],
        "legend": "Magenta circles are unmatched image-cap proposals; green circles are other stable proposals. Neither colour means physical stone truth.",
    }
    (OUT / "end6-all-cap-changes-manifest.json").write_text(json.dumps(result, indent=2) + "\n")
    print([file["path"] for file in files])


if __name__ == "__main__":
    main()
