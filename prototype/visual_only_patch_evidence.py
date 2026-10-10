"""Stone-like appearance diagnostics for unbacked event proposals."""

from statistics import median


def summarize_tracks(tracks, threshold):
    """Preserve every track score; do not turn a classifier into event truth."""
    rows = []
    for colour, track in tracks:
        points = track["points"]
        scores = [float(point["patch_score"]) for point in points]
        rows.append({
            "colour": colour,
            "interval_s": [points[0]["time_s"], points[-1]["time_s"]],
            "point_count": len(points),
            "span_px": round(track["span_px"], 3),
            "median_patch_score": round(median(scores), 5),
            "accepted_point_fraction": round(
                sum(score >= threshold for score in scores) / len(scores), 5),
            "median_patch_accepted": median(scores) >= threshold,
        })
    return rows


def patch_evidence_status(tracks):
    if not tracks:
        return "no_sustained_cap_track"
    if any(row["median_patch_accepted"] for row in tracks):
        return "stone_like_patch_track_present"
    return "cap_tracks_without_stone_like_patch_support"
