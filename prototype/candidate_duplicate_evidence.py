"""Fuse redundant visual evidence inside a counter-backed release episode."""


def contained_visual_duplicates(events, *, boundary_tolerance_s=0.25):
    """Map visual-only candidates wholly inside one counter-backed window.

    This is an event-count proposal, not proof that either candidate is false.
    Ambiguous containment in several counter events is left untouched.
    """
    counter_events = [event for event in events if event.get("counter_id")]
    duplicates = {}
    for visual in events:
        if visual.get("counter_id"):
            continue
        start, end = visual["release_window_s"]
        matches = []
        for anchor in counter_events:
            anchor_start, anchor_end = anchor["release_window_s"]
            if not (
                anchor_start - boundary_tolerance_s <= start
                and end <= anchor_end + boundary_tolerance_s
            ):
                continue
            if (
                visual.get("colour") is not None
                and anchor.get("colour") is not None
                and visual["colour"] != anchor["colour"]
            ):
                continue
            matches.append(anchor)
        if len(matches) == 1:
            anchor = matches[0]
            duplicates[visual["candidate_id"]] = {
                "primary_candidate_id": anchor["candidate_id"],
                "primary_counter_id": anchor["counter_id"],
                "reason": "visual_release_contained_in_same_colour_counter_release",
            }
    return duplicates


def fuse_candidate_events(events, duplicates):
    """Return grouped events while retaining IDs of every source candidate."""
    by_id = {event["candidate_id"]: event for event in events}
    if len(by_id) != len(events):
        raise ValueError("Duplicate candidate ID")
    groups = {identifier: [identifier] for identifier in by_id if identifier not in duplicates}
    for identifier, decision in duplicates.items():
        primary = decision["primary_candidate_id"]
        if identifier not in by_id or primary not in groups:
            raise ValueError("Duplicate decision refers to missing or absorbed primary")
        groups[primary].append(identifier)
    return [
        {
            "primary_candidate_id": identifier,
            "source_candidate_ids": sorted(ids),
            "release_window_s": by_id[identifier]["release_window_s"],
            "colour": by_id[identifier].get("colour"),
            "counter_id": by_id[identifier].get("counter_id"),
        }
        for identifier, ids in groups.items()
    ]
