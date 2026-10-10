"""Review proposals from faster, strictly consecutive right-colour tracks."""

from right_view_span_fallback import halfway_span_passage


def bidirectional_spans(
    tracks, *, displacement_px=60, max_duration_s=20, min_first_cap_area_px2=12
):
    proposals = []
    for track in tracks:
        points = track["points"]
        if not points:
            raise ValueError("Empty raw track")
        first = points[0]
        width, height = first["bbox"][2:4]
        if first["cap_area_px2"] < min_first_cap_area_px2 or width < height:
            continue
        early = [point for point in points if point["time_s"] <= first["time_s"] + max_duration_s]
        reached = next(
            (
                (i, "negative_y" if dy <= -displacement_px else "positive_y")
                for i, point in enumerate(early[1:], 1)
                if abs(dy := point["pixel"][1] - first["pixel"][1]) >= displacement_px
            ),
            None,
        )
        if reached is None:
            continue
        index, direction = reached
        prefix = early[: index + 1]
        if direction == "negative_y":
            passage = halfway_span_passage(prefix, first["pixel"][1], displacement_px)
        else:
            mirrored = [
                {**point, "pixel": [point["pixel"][0], -point["pixel"][1]]} for point in prefix
            ]
            passage = halfway_span_passage(mirrored, -first["pixel"][1], displacement_px)
            passage["pixel"][1] = -passage["pixel"][1]
        proposals.append(
            {
                "raw_track_id": track["track_id"],
                "colour_claim": track["colour"],
                "direction": direction,
                "passage_kind": "halfway_observed_motion_span_not_fixed_line",
                "passage": passage,
                "observed_prefix_interval_s": [prefix[0]["time_s"], prefix[-1]["time_s"]],
                "observed_prefix_points": prefix,
                "physical_throw_identity_verified": False,
                "simulation_ready": False,
            }
        )
    return sorted(proposals, key=lambda row: (row["passage"]["time_s"], row["raw_track_id"]))
