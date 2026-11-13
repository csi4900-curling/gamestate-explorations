"""Find a held coloured stone that begins moving in a delivery-side view."""

from math import dist
from statistics import median

import cv2

from prototype.stone_motion_fallback import stone_cap_candidates


def hold_to_motion_passages(
    observations,
    *,
    max_gap_s=0.41,
    max_step_px=65,
    min_hold_s=1.0,
    hold_radius_px=8,
    min_travel_px=35,
    max_release_span_s=1.6,
):
    """Return colour-specific release cues from timestamped cap candidates.

    Observations contain `time_s`, `colour`, and `pixel`. Track association
    stays within one shot view; callers must split at broadcast cuts.
    """
    tracks = []
    for time_s in sorted({row["time_s"] for row in observations}):
        candidates = [row for row in observations if row["time_s"] == time_s]
        used_tracks = set()
        for candidate in candidates:
            choices = []
            for index, track in enumerate(tracks):
                if index in used_tracks or track[-1]["colour"] != candidate["colour"]:
                    continue
                gap = time_s - track[-1]["time_s"]
                distance = dist(candidate["pixel"], track[-1]["pixel"])
                if 0 < gap <= max_gap_s and distance <= max_step_px:
                    choices.append((distance, index))
            if choices:
                _, index = min(choices)
                tracks[index].append(candidate)
                used_tracks.add(index)
            else:
                tracks.append([candidate])
                used_tracks.add(len(tracks) - 1)
    passages = []
    for track in tracks:
        for release_index in range(1, len(track) - 1):
            held = track[:release_index]
            if held[-1]["time_s"] - held[0]["time_s"] < min_hold_s:
                continue
            center = (
                median(row["pixel"][0] for row in held),
                median(row["pixel"][1] for row in held),
            )
            if max(dist(row["pixel"], center) for row in held) > hold_radius_px:
                continue
            if dist(track[release_index]["pixel"], center) <= hold_radius_px:
                continue
            start = held[-1]["time_s"]
            moved = [
                row for row in track[release_index:] if row["time_s"] - start <= max_release_span_s
            ]
            if len(moved) < 2:
                continue
            distance = max(dist(row["pixel"], center) for row in moved)
            if distance < min_travel_px:
                continue
            passages.append(
                {
                    "colour": track[0]["colour"],
                    "held_interval_s": [held[0]["time_s"], start],
                    "release_cue_s": moved[0]["time_s"],
                    "moving_interval_s": [moved[0]["time_s"], moved[-1]["time_s"]],
                    "held_center_px": [round(value, 2) for value in center],
                    "max_travel_px": round(distance, 2),
                    "track_observation_count": len(track),
                }
            )
            break
    return sorted(passages, key=lambda row: (row["release_cue_s"], row["colour"]))


def scan_origin_release(cap, fps, start_s, end_s, *, cut_times_s=()):
    """Sample the delivery-side lower ice for a held-cap release passage."""
    observations = []
    for tick in range(round(start_s * 5), round(end_s * 5)):
        time_s = round(tick / 5, 3)
        cap.set(cv2.CAP_PROP_POS_FRAMES, round(time_s * fps))
        ok, frame = cap.read()
        if not ok:
            raise RuntimeError(f"Frame decode failed at {time_s}")
        for colour in ("red", "yellow"):
            candidates = stone_cap_candidates(
                frame, colour, allow_large_caps=True, allow_bright_body=True
            )
            for item in candidates:
                x, y = item["pixel"]
                _, _, width, height = item["bbox"]
                if (
                    200 <= x <= 550
                    and y >= 240
                    and width <= 70
                    and height <= 35
                    and item["neutral_surround_fraction"] >= 0.25
                ):
                    observations.append(
                        {"time_s": time_s, "colour": colour, "pixel": item["pixel"]}
                    )
    segments = [[]]
    cuts = sorted(cut for cut in cut_times_s if start_s < cut < end_s)
    for observation in sorted(observations, key=lambda row: row["time_s"]):
        while cuts and observation["time_s"] >= cuts[0]:
            segments.append([])
            cuts.pop(0)
        segments[-1].append(observation)
    passages = [passage for segment in segments for passage in hold_to_motion_passages(segment)]
    return {
        "sampled_frame_count": round(end_s * 5) - round(start_s * 5),
        "filtered_cap_observation_count": len(observations),
        "passages": sorted(passages, key=lambda row: row["release_cue_s"]),
    }
