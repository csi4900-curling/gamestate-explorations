"""Find visual stone-motion candidates inside unsupported Beijing layout gaps."""

from stone_motion_fallback import moving_cap_tracks


def interior_beijing_gaps(runs):
    """Choose unknown spans bracketed by Beijing-supported runs."""
    gaps = []
    for index, run in enumerate(runs):
        if run["layout"] != "unknown" or index == 0 or index == len(runs) - 1:
            continue
        before = runs[index - 1]
        after = runs[index + 1]
        if before["layout"] == after["layout"] == "beijing_2022":
            if (
                before["interval_s"][1] != run["interval_s"][0]
                or run["interval_s"][1] != after["interval_s"][0]
            ):
                raise ValueError("Noncontiguous layout runs")
            gaps.append(run["interval_s"])
    return gaps


def candidates_from_observations(
    observations_by_colour, gap_id, gap_interval, *, tracker_max_gap_s=2.0,
    tracker_max_step_px=25.0, cut_times_s=()
):
    """Keep every sustained visual track as an unconfirmed candidate."""
    candidates = []
    for colour in ("red", "yellow"):
        tracks = moving_cap_tracks(
            observations_by_colour[colour],
            max_gap_s=tracker_max_gap_s,
            max_step_px=tracker_max_step_px,
            cut_times_s=cut_times_s,
        )
        for index, track in enumerate(tracks, 1):
            points = track["points"]
            start_s, end_s = points[0]["time_s"], points[-1]["time_s"]
            if not gap_interval[0] <= start_s <= end_s < gap_interval[1]:
                raise ValueError("Visual track crosses unsupported interval boundary")
            candidates.append(
                {
                    "id": f"{gap_id}-{colour[0].upper()}{index:02}",
                    "gap_id": gap_id,
                    "colour": colour,
                    "crossing_time_s": start_s,
                    "evidence_interval_s": [start_s, end_s],
                    "evidence_kind": "visual_stone_cap_motion_in_unsupported_layout",
                    "status": "unconfirmed_gap_motion_candidate",
                    "release_time_s": None,
                    "visual_track_span_px": track["span_px"],
                    "visual_track_points": points,
                }
            )
    return sorted(candidates, key=lambda row: (row["crossing_time_s"], row["id"]))
