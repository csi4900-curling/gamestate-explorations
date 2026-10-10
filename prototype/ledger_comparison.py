"""Compare two candidate ledgers without treating shot IDs as stable identity."""


def compare_ledgers(baseline, augmented):
    """Match counter-backed events by counter ID and expose other changes.

    Visual-only events are deliberately not force-matched: overlapping release
    windows can contain multiple physical deliveries when a camera shot was
    undersegmented.
    """
    def index_counter(events):
        indexed = {}
        for event in events:
            key = event.get("counter_id")
            if key:
                if key in indexed:
                    raise ValueError(f"Duplicate counter ID: {key}")
                indexed[key] = event
        return indexed

    old = index_counter(baseline)
    new = index_counter(augmented)
    counter_changes = []
    for key in sorted(set(old) | set(new)):
        before, after = old.get(key), new.get(key)
        if before is None or after is None:
            counter_changes.append({"counter_id": key, "change": "missing_in_one_run",
                                    "baseline": before, "augmented": after})
            continue
        colour_changed = before.get("colour") != after.get("colour")
        window_changed = before["release_window_s"] != after["release_window_s"]
        if colour_changed or window_changed:
            counter_changes.append({
                "counter_id": key,
                "change": "colour_changed" if colour_changed else "window_changed",
                "baseline": {"shot_id": before["shot_id"],
                             "release_window_s": before["release_window_s"],
                             "colour": before.get("colour")},
                "augmented": {"shot_id": after["shot_id"],
                              "release_window_s": after["release_window_s"],
                              "colour": after.get("colour")},
            })

    def visual_only(events, other_events):
        rows = []
        for event in events:
            if event.get("counter_id"):
                continue
            start, end = event["release_window_s"]
            overlaps = []
            for other in other_events:
                other_start, other_end = other["release_window_s"]
                if max(start, other_start) < min(end, other_end):
                    overlaps.append({"candidate_id": other["candidate_id"],
                                     "counter_id": other.get("counter_id"),
                                     "colour": other.get("colour"),
                                     "release_window_s": other["release_window_s"]})
            rows.append({"candidate_id": event["candidate_id"],
                         "shot_id": event["shot_id"],
                         "release_window_s": event["release_window_s"],
                         "colour": event.get("colour"),
                         "opposite_run_overlaps": overlaps})
        return rows

    return {
        "baseline_count": len(baseline),
        "augmented_count": len(augmented),
        "baseline_counter_backed": len(old),
        "augmented_counter_backed": len(new),
        "counter_changes": counter_changes,
        "baseline_visual_only": visual_only(baseline, augmented),
        "augmented_visual_only": visual_only(augmented, baseline),
        "limitations": [
            "Counter IDs are broadcast evidence, not independently timed throw identities.",
            "Visual-only candidates are not force-matched by shot ID or interval overlap.",
            "A release window can contain more than one physical throw when a camera shot is undersegmented.",
        ],
    }
