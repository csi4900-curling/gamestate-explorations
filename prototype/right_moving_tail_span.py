"""Extract a sustained short moving tail from long right-colour review paths."""

from right_bidirectional_span import bidirectional_spans


def moving_tail_spans(probe, *, long_prefix_s=10, tail_limit_s=5,
                      min_points=3, min_signed_step_px=8):
    """Keep every proposal; trim only long prefixes with a moving tail.

    This can remove a stationary-to-moving track splice from the displayed
    evidence, but cannot establish that both portions depict one stone.
    """
    tracks = {row["track_id"]: row for row in probe["raw_tracks"]}
    if len(tracks) != len(probe["raw_tracks"]):
        raise ValueError("Duplicate raw track ID")
    rows = []
    for original in probe["directional_review_proposals"]:
        track = tracks[original["raw_track_id"]]
        start, stop = original["observed_prefix_interval_s"]
        chosen = None
        if stop - start > long_prefix_s:
            points = track["points"]
            for seed in range(original["seed_start_index"] + 1, len(points)):
                found = bidirectional_spans([{**track, "points": points[seed:]}],
                                            max_duration_s=tail_limit_s)
                if not found:
                    continue
                candidate = found[0]
                prefix = candidate["observed_prefix_points"]
                sign = 1 if original["direction"] == "positive_y" else -1
                if (candidate["direction"] != original["direction"]
                        or len(prefix) < min_points
                        or any(sign * (b["pixel"][1] - a["pixel"][1]) <
                               min_signed_step_px
                               for a, b in zip(prefix, prefix[1:]))):
                    continue
                chosen = {**candidate, "seed_start_index": seed,
                          "seed_kind": "latest_sustained_moving_tail",
                          "original_review_passage_time_s": original[
                              "passage"]["time_s"],
                          "original_review_prefix_interval_s": [start, stop],
                          "tail_extraction_status": "short_sustained_motion_from_long_prefix"}
        if chosen is None:
            chosen = {**original, "tail_extraction_status": (
                "no_supported_short_tail_retained" if stop - start > long_prefix_s
                else "original_short_prefix_retained")}
        rows.append(chosen)
    return sorted(rows, key=lambda row: (row["passage"]["time_s"],
                                         row["raw_track_id"]))
