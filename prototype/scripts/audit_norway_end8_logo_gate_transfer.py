"""Coverage probe: can the button logo inform origin-gate side routing?"""

from hashlib import sha256
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.button_logo_orientation import logo_colour_signature
from prototype.scripts.audit_china_end2_wide_view_caps import wide_house_ellipse
from prototype.video_board_observation_v2 import detect_overhead_house

BASE = ROOT / "validation/curlobserver-learned-probe/cap-patch-crossmatch-v1"
VIDEO = ROOT / "validation/throw-event-benchmark/paralympics-2022-canada-norway/source.mp4"
GATES = BASE / "norway-end8-dual-gate-events-first.json"
PLAN = BASE / "norway-end8-logo-gate-transfer-plan.json"
OUTPUT = BASE / "norway-end8-logo-gate-coverage-first.json"
FRACTIONS = (0.2, 0.5, 0.8)


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first logo-gate coverage probe")
    plan = json.loads(PLAN.read_text())
    files = {
        "video": VIDEO,
        "gates": GATES,
        "logo_code": ROOT / "prototype/button_logo_orientation.py",
        "overhead_house_code": ROOT / "prototype/video_board_observation_v2.py",
        "wide_house_code": ROOT / "prototype/scripts/audit_china_end2_wide_view_caps.py",
        "runner": Path(__file__),
    }
    hashes = {name: digest(path) for name, path in files.items()}
    if hashes != plan["frozen_sha256"]:
        raise ValueError("Frozen transfer input changed")
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    if hashes["video"] == reserved["source_sha256"]:
        raise ValueError("Reserved source selected")
    gates = json.loads(GATES.read_text())
    if (
        gates["source_sha256"] != hashes["video"]
        or gates["end"] != 8
        or [row["shot_id"] for row in gates["decisions"]] != plan["shot_ids"]
        or [row["interval_s"] for row in gates["decisions"]] != plan["intervals_s"]
    ):
        raise ValueError("Predeclared shot selection changed")
    capture = cv2.VideoCapture(str(VIDEO), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    fps = capture.get(cv2.CAP_PROP_FPS)
    rows = []
    for decision in gates["decisions"]:
        start, end = decision["interval_s"]
        frames = []
        for fraction in FRACTIONS:
            time_s = start + fraction * (end - start)
            capture.set(cv2.CAP_PROP_POS_FRAMES, round(time_s * fps))
            ok, frame = capture.read()
            if not ok:
                raise RuntimeError(f"Cannot decode {time_s} s")
            frame = cv2.resize(frame, (640, 360))
            overhead = detect_overhead_house(frame)
            if overhead is not None:
                center = overhead["center_px"]
                axes = [overhead["outer_radius_px"]] * 2
                route = "overhead_house"
            else:
                wide = wide_house_ellipse(frame)
                if wide is not None:
                    center = wide["center_px"]
                    axes = [max(wide["axis_lengths_px"]) / 2, min(wide["axis_lengths_px"]) / 2]
                    route = "wide_house"
                else:
                    center, axes, route = None, None, "no_house"
            signature = logo_colour_signature(frame, center, axes) if center is not None else None
            frames.append(
                {
                    "sample_fraction": fraction,
                    "time_s": round(time_s, 3),
                    "house_route": route,
                    "house_center_px": center,
                    "house_outer_axes_px": axes,
                    "logo_signature": signature,
                }
            )
        signatures = [
            frame["logo_signature"] for frame in frames if frame["logo_signature"] is not None
        ]
        sign_pairs = {
            (row["red_lateral_sign"], row["red_minus_blue_vertical_sign"]) for row in signatures
        }
        rows.append(
            {
                "shot_id": decision["shot_id"],
                "interval_s": decision["interval_s"],
                "source_only_gate_side": decision["side"],
                "source_only_gate_side_route": decision["side_route"],
                "sampled_frames": frames,
                "logo_supported_frame_count": len(signatures),
                "unanimous_logo_sign_pair": list(next(iter(sign_pairs)))
                if len(signatures) >= 2 and len(sign_pairs) == 1
                else None,
            }
        )
    capture.release()
    output = {
        "status": "first_selected_end8_logo_coverage_probe_not_gate_rule",
        "source_sha256": hashes["video"],
        "plan_sha256": digest(PLAN),
        "frozen_sha256": hashes,
        "sample_fractions": list(FRACTIONS),
        "rows": rows,
        "limitations": [
            "End eight was exposed in previous gate development; this probes cue availability, not held-out event accuracy.",
            "The logo cue was built on selected China and Swiss board views before this Norway scan.",
            "No gate decision is modified and no counter or official throw labels are used.",
            "A logo sign does not by itself imply left or right delivery gate; correlation is descriptive only.",
            "Three sampled frames per origin shot cannot prove full-shot logo coverage.",
        ],
    }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n")
    print(
        {
            "shots": len(rows),
            "any_logo": sum(row["logo_supported_frame_count"] > 0 for row in rows),
            "unanimous_two_plus": sum(row["unanimous_logo_sign_pair"] is not None for row in rows),
            "house_frames": sum(
                frame["house_route"] != "no_house"
                for row in rows
                for frame in row["sampled_frames"]
            ),
        }
    )


if __name__ == "__main__":
    main()
