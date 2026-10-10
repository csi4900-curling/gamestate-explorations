"""Extract later review spans after a quiet period in one raw colour track.

A raw track is a sequence of colour blobs, not a persistent stone identity.
Multiple episodes remain independent image-motion proposals for source review.
"""

from right_late_seed_span import late_seed_bidirectional_spans


def _first_quiet_end(
    points, after_index, *, quiet_steps=3, quiet_rate_px_s=3, max_sample_gap_s=1.5
):
    for end_index in range(after_index + quiet_steps, len(points)):
        steps = []
        for before, current in zip(
            points[end_index - quiet_steps : end_index],
            points[end_index - quiet_steps + 1 : end_index + 1],
        ):
            dt = current["time_s"] - before["time_s"]
            if dt <= 0:
                raise ValueError("Raw track times must increase")
            steps.append((dt, abs(current["pixel"][1] - before["pixel"][1]) / dt))
        if all(dt <= max_sample_gap_s and rate <= quiet_rate_px_s for dt, rate in steps):
            return end_index
    return None


def multi_episode_spans(tracks, *, quiet_steps=3, quiet_rate_px_s=3, max_sample_gap_s=1.5):
    proposals = []
    for track in tracks:
        points = track["points"]
        if not points:
            raise ValueError("Empty raw track")
        if any(
            current["time_s"] <= previous["time_s"] for previous, current in zip(points, points[1:])
        ):
            raise ValueError("Raw track times must increase")
        suffix_start = 0
        quiet_end = None
        episode_index = 0
        while suffix_start < len(points):
            suffix = {**track, "points": points[suffix_start:]}
            found = late_seed_bidirectional_spans([suffix])
            if not found:
                break
            proposal = found[0]
            episode_index += 1
            proposal["episode_index_within_raw_track"] = episode_index
            proposal["preceding_quiet_end_time_s"] = (
                points[quiet_end]["time_s"] if quiet_end is not None else None
            )
            proposal["raw_track_not_physical_identity"] = True
            proposals.append(proposal)
            last_time = proposal["observed_prefix_interval_s"][1]
            end_indices = [i for i, point in enumerate(points) if point["time_s"] == last_time]
            if len(end_indices) != 1:
                raise ValueError("Proposal end does not locate a unique raw point")
            quiet_end = _first_quiet_end(
                points,
                end_indices[0],
                quiet_steps=quiet_steps,
                quiet_rate_px_s=quiet_rate_px_s,
                max_sample_gap_s=max_sample_gap_s,
            )
            if quiet_end is None:
                break
            suffix_start = quiet_end
    return sorted(
        proposals,
        key=lambda row: (
            row["passage"]["time_s"],
            row["raw_track_id"],
            row["episode_index_within_raw_track"],
        ),
    )
