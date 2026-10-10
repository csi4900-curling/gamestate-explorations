"""Line-free right-camera motion-span proposals from preserved colour tracks."""


def halfway_span_passage(prefix, first_y, displacement_px):
    """Interpolate the observed halfway point; it is not a rink gate time."""
    target_y = first_y - displacement_px / 2
    for before, after in zip(prefix, prefix[1:]):
        y0, y1 = before["pixel"][1], after["pixel"][1]
        if y0 >= target_y >= y1 and y0 != y1:
            fraction = (y0 - target_y) / (y0 - y1)
            return {
                "time_s": round(before["time_s"] + fraction *
                                (after["time_s"] - before["time_s"]), 3),
                "pixel": [round(before["pixel"][0] + fraction *
                                (after["pixel"][0] - before["pixel"][0]), 2),
                          round(target_y, 2)],
                "bracket_s": [before["time_s"], after["time_s"]],
            }
    raise ValueError("Observed prefix does not cross its halfway displacement")


def span_fallback(tracks, existing_ids, *, displacement_px=60,
                  max_delay_s=20, min_first_cap_area_px2=12):
    """Preserve the line-based tier; add only tracks it omitted."""
    output = []
    existing_ids = list(existing_ids)
    if len(existing_ids) != len(set(existing_ids)):
        raise ValueError("Duplicate existing track ID")
    existing_ids = set(existing_ids)
    seen = set()
    for track in tracks:
        track_id = track["track_id"]
        if track_id in seen:
            raise ValueError("Duplicate raw track ID")
        seen.add(track_id)
        if track_id in existing_ids:
            continue
        points = track["points"]
        if len(points) < 2:
            continue
        first = points[0]
        width, height = first["bbox"][2:4]
        if first["cap_area_px2"] < min_first_cap_area_px2 or width < height:
            continue
        early = [point for point in points
                 if point["time_s"] <= first["time_s"] + max_delay_s]
        reached = next((index for index, point in enumerate(early[1:], 1)
                        if first["pixel"][1] - point["pixel"][1] >= displacement_px), None)
        if reached is None:
            continue
        prefix = early[:reached + 1]
        passage = halfway_span_passage(prefix, first["pixel"][1], displacement_px)
        output.append({
            "raw_track_id": track_id,
            "colour_claim": track["colour"],
            "passage_kind": "halfway_observed_upward_motion_span_not_fixed_line",
            "passage": passage,
            "observed_prefix_interval_s": [prefix[0]["time_s"], prefix[-1]["time_s"]],
            "observed_prefix_points": prefix,
            "physical_throw_identity_verified": False,
            "simulation_ready": False,
        })
    return sorted(output, key=lambda row: (row["passage"]["time_s"],
                                           row["raw_track_id"]))
