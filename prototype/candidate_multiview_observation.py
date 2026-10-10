"""Join candidate-local camera observations without claiming physical segments."""

from statistics import median


def build_observation_windows(sequence, left_tracks, right_proposals):
    sources = {item["source_sha256"] for item in (sequence, left_tracks, right_proposals)}
    if len(sources) != 1:
        raise ValueError("Input source hashes disagree")
    left = {track["event_id"]: track for track in left_tracks["tracks"]}
    right = {proposal["raw_track_id"]: proposal
             for proposal in right_proposals["entry_review_proposals"]}
    if len(left) != len(left_tracks["tracks"]) or len(right) != len(right_proposals["entry_review_proposals"]):
        raise ValueError("Duplicate source track ID")

    rows = []
    gaps = []
    for candidate in sequence["rows"]:
        candidate_id = candidate["candidate_id"]
        timestamp = candidate["observation_time_s"]
        colour = candidate["colour_claim"]
        left_span = None
        right_span = None
        right_id = candidate["right_entry"]["raw_track_id"] if candidate["right_entry"] else None

        if candidate["observation_kind"] == "left_tracked_crossing":
            event_id = candidate_id.rsplit("-", 1)[-1]
            track = left[event_id]
            left_span = [track["first_track_observation_s"], track["last_track_observation_s"]]
            if track["colour"] != colour or abs(track["crossing_time_s"] - timestamp) > .001:
                raise ValueError(f"Left crossing disagrees: {candidate_id}")
            if not left_span[0] <= timestamp <= left_span[1]:
                raise ValueError(f"Left crossing outside observed track: {candidate_id}")
        elif candidate["observation_kind"] != "right_entry_crossing":
            raise ValueError(f"Unknown observation kind: {candidate_id}")

        if right_id is not None:
            proposal = right[right_id]
            right_span = proposal["observed_prefix_interval_s"]
            entry = proposal["entry_crossing"]["time_s"]
            if proposal["colour_claim"] != colour or abs(entry - candidate["right_entry"]["entry_time_s"]) > .001:
                raise ValueError(f"Right entry disagrees: {candidate_id}")
            if not right_span[0] <= entry <= right_span[1]:
                raise ValueError(f"Right entry outside observed prefix: {candidate_id}")
            if left_span is None and abs(entry - timestamp) > .001:
                raise ValueError(f"Right-only observation time disagrees: {candidate_id}")
        elif left_span is None:
            raise ValueError(f"Candidate has no source observation: {candidate_id}")

        seam = None
        if left_span is not None and right_span is not None:
            if right_span[0] < left_span[1]:
                raise ValueError(f"Overlapping camera spans: {candidate_id}")
            seam = [left_span[1], right_span[0]]
            gaps.append(round(seam[1] - seam[0], 3))
        envelope = [left_span[0] if left_span is not None else right_span[0],
                    right_span[1] if right_span is not None else left_span[1]]
        rows.append({
            "candidate_id": candidate_id,
            "sequence_proposal_id": candidate["sequence_proposal_id"],
            "colour_claim": colour,
            "right_raw_track_id": right_id,
            "evidence_tier": candidate["evidence_tier"],
            "source_crossing_class": candidate["crossing_source_class"],
            "left_observed_track_interval_s": left_span,
            "right_observed_prefix_interval_s": right_span,
            "unobserved_camera_seam_s": seam,
            "unobserved_camera_seam_duration_s": round(seam[1] - seam[0], 3) if seam else None,
            "candidate_observation_envelope_s": envelope,
            "physical_cross_camera_identity_verified": False,
            "release_time_s": None,
            "physical_settle_time_s": None,
            "physical_throw_segment_verified": False,
            "simulation_ready": False,
        })
    if len(rows) != sequence["candidate_sequence_count"]:
        raise ValueError("Sequence count disagrees")
    return {
        "status": "candidate_multiview_observation_windows_not_physical_throw_segments",
        "source_sha256": sources.pop(),
        "candidate_count": len(rows),
        "two_view_candidate_count": len(gaps),
        "median_unobserved_camera_seam_s": round(median(gaps), 3) if gaps else None,
        "minimum_unobserved_camera_seam_s": min(gaps, default=None),
        "maximum_unobserved_camera_seam_s": max(gaps, default=None),
        "rows": rows,
        "limitations": [
            "Camera tracks are colour-blob associations; conditional links do not prove persistent stone identity.",
            "The observation envelope is neither a physical release/settle window nor a complete trajectory.",
            "Unobserved camera seams must not be filled with interpolated ground truth.",
            "Source crossing classes are development reviews, not independent event labels.",
        ],
    }
