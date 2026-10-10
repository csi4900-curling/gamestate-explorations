"""Group nearby same-colour/direction image passages for review, not truth."""


def group_candidate_passages(events, *, max_group_span_s=25):
    if max_group_span_s <= 0:
        raise ValueError("Invalid group span")
    ordered = sorted(events, key=lambda row: row["crossing_time_s"])
    if len({row["id"] for row in ordered}) != len(ordered):
        raise ValueError("Duplicate candidate ID")
    groups = []
    for event in ordered:
        if (
            groups
            and event["colour"] == groups[-1]["colour"]
            and event["view_motion"] == groups[-1]["view_motion"]
            and event["crossing_time_s"] - groups[-1]["first_time_s"] <= max_group_span_s
        ):
            groups[-1]["member_ids"].append(event["id"])
            groups[-1]["last_time_s"] = event["crossing_time_s"]
        else:
            groups.append(
                {
                    "colour": event["colour"],
                    "view_motion": event["view_motion"],
                    "first_time_s": event["crossing_time_s"],
                    "last_time_s": event["crossing_time_s"],
                    "member_ids": [event["id"]],
                }
            )
    for index, group in enumerate(groups, 1):
        group["group_id"] = f"G{index:03d}"
        group["physical_throw_verified"] = False
    return groups
