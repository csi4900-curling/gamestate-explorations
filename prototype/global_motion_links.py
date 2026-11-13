"""Link candidate windows to a source-wide shot-scoped motion catalog.

This constructs an evidence graph. It never assigns physical throws or stone
identities from temporal overlap alone.
"""

from collections import Counter, defaultdict


def overlaps_interval(track_interval, window):
    """Tracks include their final sample; search windows exclude their end."""
    first, last = track_interval
    start, end = window
    return first < end and last >= start


def link_candidate_windows(candidates, shot_rows):
    episode_rows = [episode for shot in shot_rows for episode in shot["tracks"]]
    ids = [episode["episode_id"] for episode in episode_rows]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate global episode ID")
    for shot in shot_rows:
        start, end = shot["interval_s"]
        for episode in shot["tracks"]:
            first, last = episode["interval_s"]
            if (
                episode["camera_shot_id"] != shot["camera_shot_id"]
                or not start <= first <= last < end
            ):
                raise ValueError(
                    f"Episode crosses or misidentifies camera shot: {episode['episode_id']}"
                )
    candidate_ids = [row["shot_id"] for row in candidates]
    if len(candidate_ids) != len(set(candidate_ids)):
        raise ValueError("Duplicate candidate ID")
    edges = []
    by_candidate = defaultdict(list)
    by_episode = defaultdict(list)
    for candidate in candidates:
        colour = candidate["candidate_colour"]
        if colour not in (None, "red", "yellow"):
            raise ValueError(f"Unknown candidate colour: {colour}")
        for episode in episode_rows:
            if colour is not None and episode["colour"] != colour:
                continue
            if not overlaps_interval(episode["interval_s"], candidate["search_interval_s"]):
                continue
            edge = {
                "candidate_id": candidate["shot_id"],
                "episode_id": episode["episode_id"],
                "same_origin_camera_shot": candidate["shot_id"] == episode["camera_shot_id"],
                "overlaps_delivery_window": overlaps_interval(
                    episode["interval_s"], candidate["delivery_window_s"]
                ),
                "link_basis": "compatible_colour_and_search_time_overlap_only",
                "physical_throw_assignment_verified": False,
            }
            edges.append(edge)
            by_candidate[candidate["shot_id"]].append(episode["episode_id"])
            by_episode[episode["episode_id"]].append(candidate["shot_id"])
    episode_links = [
        {
            "episode_id": episode["episode_id"],
            "camera_shot_id": episode["camera_shot_id"],
            "colour": episode["colour"],
            "interval_s": episode["interval_s"],
            "candidate_ids": sorted(by_episode[episode["episode_id"]]),
            "physical_stone_identity_verified": False,
        }
        for episode in episode_rows
    ]
    candidate_links = []
    for candidate in candidates:
        linked = sorted(by_candidate[candidate["shot_id"]])
        exclusive = [episode_id for episode_id in linked if len(by_episode[episode_id]) == 1]
        status = (
            "exclusive_catalogue_track_available"
            if exclusive
            else ("shared_catalogue_tracks_only" if linked else "no_catalogue_track")
        )
        candidate_links.append(
            {
                "candidate_id": candidate["shot_id"],
                "counter_id": candidate["counter_id"],
                "catalogue_motion_status": status,
                "linked_episode_ids": linked,
                "exclusive_episode_ids": exclusive,
                "distinct_throw_verified": False,
            }
        )
    return {
        "catalogue_episode_count": len(episode_rows),
        "candidate_count": len(candidates),
        "candidate_episode_edge_count": len(edges),
        "shared_by_multiple_candidates_episode_count": sum(
            len(row["candidate_ids"]) > 1 for row in episode_links
        ),
        "unlinked_catalogue_episode_count": sum(not row["candidate_ids"] for row in episode_links),
        "candidate_motion_status_counts": dict(
            Counter(row["catalogue_motion_status"] for row in candidate_links)
        ),
        "episodes": episode_links,
        "candidates": candidate_links,
        "edges": edges,
    }
