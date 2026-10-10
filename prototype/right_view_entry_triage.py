"""Development-only early crossing proposals from right-view raw tracks."""


def crossing(points, threshold):
    """Interpolate the image-line crossing between observed upward samples."""
    for before, after in zip(points, points[1:]):
        y0, y1 = before["pixel"][1], after["pixel"][1]
        if y0 > threshold >= y1 and y1 != y0:
            alpha = (y0 - threshold) / (y0 - y1)
            return {"time_s": round(before["time_s"] + alpha *
                                    (after["time_s"] - before["time_s"]), 3),
                    "x_px": round(before["pixel"][0] + alpha *
                                  (after["pixel"][0] - before["pixel"][0]), 2),
                    "bracket_s": [before["time_s"], after["time_s"]]}
    return None


def triage_tracks(tracks):
    """Keep entry-like prefixes while retaining all raw track IDs elsewhere."""
    proposals = []
    for track in tracks:
        points = track["points"]
        if not points:
            raise ValueError("Empty raw track")
        first = points[0]
        width, height = first["bbox"][2:4]
        if (first["pixel"][1] < 250 or first["cap_area_px2"] < 12 or
                width < height):
            continue
        early = [point for point in points
                 if point["time_s"] <= first["time_s"] + 20]
        reached = next((i for i, point in enumerate(early[1:], 1)
                        if point["pixel"][1] <= 220 and
                        first["pixel"][1] - point["pixel"][1] >= 60), None)
        if reached is None:
            continue
        prefix = early[:reached + 1]
        entry = crossing(prefix, 250)
        if entry is None:
            continue
        proposals.append({
            "raw_track_id": track["track_id"],
            "colour_claim": track["colour"],
            "entry_line_y_px": 250,
            "entry_crossing": entry,
            "confirmation_time_s": prefix[-1]["time_s"],
            "confirmation_rule": "Observed at y<=220 within 20 s with >=60 px upward displacement from first observation.",
            "observed_prefix_interval_s": [prefix[0]["time_s"], prefix[-1]["time_s"]],
            "observed_prefix_points": prefix,
            "physical_throw_identity_verified": False,
            "release_time_s": None,
            "physical_settle_time_s": None,
            "simulation_ready": False,
        })
    return sorted(proposals, key=lambda row: (row["entry_crossing"]["time_s"],
                                              row["raw_track_id"]))
