"""Deduplicate identical local motion tracks into a global episode registry."""

from collections import Counter, defaultdict


def track_key(colour, track):
    """Exact fingerprint; no cross-cut or near-track identity is inferred."""
    return (colour, track["first_seen_s"], track["last_seen_s"],
            track["span_px"], track["point_count"],
            tuple(track["first_pixel"]), tuple(track["last_pixel"]))


def build_registry(candidate_rows):
    by_key = defaultdict(list)
    seen_events = set()
    for event in candidate_rows:
        shot_id = event["shot_id"]
        if shot_id in seen_events:
            raise ValueError(f"Duplicate candidate ID: {shot_id}")
        seen_events.add(shot_id)
        for colour in ("red", "yellow"):
            for track in event["colour_tracks"][colour]:
                by_key[track_key(colour, track)].append(shot_id)
    ordered = sorted(by_key, key=lambda key: (key[1], key[0], key[2], key[5], key[6]))
    ids = {key: f"M{i:04}" for i, key in enumerate(ordered, 1)}
    episodes = []
    for key in ordered:
        candidate_ids = sorted(set(by_key[key]))
        episodes.append({"episode_id": ids[key], "colour": key[0],
                         "motion_interval_s": [key[1], key[2]],
                         "span_px": key[3], "point_count": key[4],
                         "first_pixel": list(key[5]), "last_pixel": list(key[6]),
                         "candidate_ids": candidate_ids,
                         "candidate_assignment_status": "unique_candidate" if len(candidate_ids) == 1
                             else "shared_by_multiple_candidates",
                         "physical_stone_identity_verified": False})
    event_rows = []
    for event in candidate_rows:
        keys = {track_key(colour, track) for colour in ("red", "yellow")
                for track in event["colour_tracks"][colour]}
        exclusive = sorted(ids[key] for key in keys if len(set(by_key[key])) == 1)
        shared = sorted(ids[key] for key in keys if len(set(by_key[key])) > 1)
        status = "exclusive_track_available" if exclusive else "shared_tracks_only" if shared else "no_supported_track"
        event_rows.append({"shot_id": event["shot_id"], "counter_id": event["counter_id"],
                           "motion_support_status": status,
                           "exclusive_episode_ids": exclusive,
                           "shared_episode_ids": shared,
                           "distinct_throw_verified": False})
    counts = Counter(row["motion_support_status"] for row in event_rows)
    return {"episode_count": len(episodes),
            "shared_episode_count": sum(len(row["candidate_ids"]) > 1 for row in episodes),
            "candidate_motion_status_counts": dict(counts),
            "episodes": episodes, "candidates": event_rows}
