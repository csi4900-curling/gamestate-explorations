"""Development fallback: seek a later valid seed in an existing raw track."""

from right_bidirectional_span import bidirectional_spans


def late_seed_bidirectional_spans(tracks, *, displacement_px=60,
                                  max_duration_s=20,
                                  min_first_cap_area_px2=12):
    proposals = []
    for track in tracks:
        points = track["points"]
        if not points:
            raise ValueError("Empty raw track")
        for seed_index, point in enumerate(points):
            width, height = point["bbox"][2:4]
            if point["cap_area_px2"] < min_first_cap_area_px2 or width < height:
                continue
            candidate = {**track, "points": points[seed_index:]}
            found = bidirectional_spans(
                [candidate], displacement_px=displacement_px,
                max_duration_s=max_duration_s,
                min_first_cap_area_px2=min_first_cap_area_px2)
            if found:
                proposal = found[0]
                proposal["seed_start_index"] = seed_index
                proposal["seed_kind"] = ("original_first_point" if seed_index == 0
                                         else "later_valid_raw_track_point")
                proposals.append(proposal)
                break
    return sorted(proposals, key=lambda row: (row["passage"]["time_s"],
                                              row["raw_track_id"]))
