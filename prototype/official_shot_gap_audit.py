"""Locate official shots without a clean broadcast-counter anchor."""


def build_gap_runs(game, counter_rows, candidate_events):
    """Group missing official IDs and attach nearby evidence for video review.

    Anchor times are delayed counter observations, not throw timestamps. A
    bounded search span is only a practical place to inspect the video.
    """
    runs = []
    for end in game["ends"]:
        end_number = end["end"]
        rows = [row for row in counter_rows if row["official_end"] == end_number]
        clean = {"unique_colour_concordant", "unique_colour_concordant_amid_duplicate"}
        anchors = {row["inferred_shot_number"]: row for row in rows if row["status"] in clean}
        uncovered = [number for number in range(1, end["shot_count"] + 1) if number not in anchors]
        groups = []
        for number in uncovered:
            if groups and number == groups[-1][-1] + 1:
                groups[-1].append(number)
            else:
                groups.append([number])
        for numbers in groups:
            before = anchors.get(numbers[0] - 1)
            after = anchors.get(numbers[-1] + 1)
            left = before["counter_time_s"] if before else None
            right = after["counter_time_s"] if after else None
            if left is not None and right is not None and right <= left:
                raise ValueError("Official counter anchors are not chronological")
            conflicts = [row for row in rows if row["inferred_shot_number"] in numbers]
            nearby = []
            if left is not None and right is not None:
                for candidate in candidate_events:
                    window = candidate.get("release_window_s")
                    if window and window[0] <= right and window[1] >= left:
                        nearby.append(
                            {
                                "candidate_id": candidate["candidate_id"],
                                "release_window_s": window,
                                "colour": candidate.get("colour"),
                                "counter_id": candidate.get("counter_id"),
                            }
                        )
            unlinked = [candidate for candidate in nearby if candidate["counter_id"] is None]
            if len(numbers) == 1 and len(unlinked) == 1:
                expected = game["team_handle_colours"][end["shots"][numbers[0] - 1]["team"]]
                observed = unlinked[0]["colour"]
                triage = (
                    "single_visual_candidate_colour_unknown"
                    if observed is None
                    else "single_visual_candidate_colour_match"
                    if observed == expected
                    else "single_visual_candidate_colour_conflict"
                )
            elif unlinked:
                triage = "multiple_or_multishot_visual_candidates"
            else:
                triage = "no_unlinked_visual_candidate"
            runs.append(
                {
                    "official_end": end_number,
                    "first_shot_number": numbers[0],
                    "last_shot_number": numbers[-1],
                    "official_shots": [
                        {
                            "official_shot_id": end["shots"][number - 1]["official_shot_id"],
                            "team": end["shots"][number - 1]["team"],
                            "colour": game["team_handle_colours"][end["shots"][number - 1]["team"]],
                        }
                        for number in numbers
                    ],
                    "left_anchor_counter_id": before["counter_id"] if before else None,
                    "right_anchor_counter_id": after["counter_id"] if after else None,
                    "review_search_span_s": [left, right],
                    "bounded_within_end": left is not None and right is not None,
                    "conflicting_counter_ids": [row["counter_id"] for row in conflicts],
                    "candidate_windows_intersecting_span": nearby,
                    "visual_candidate_triage": triage,
                }
            )
    return runs
