"""Group left proposals that compete for the same right-camera proposal."""


def build_corrob_episodes(rows, *, right_proposals=None, interval_s=None):
    by_left = {row["left_candidate_id"]: row for row in rows}
    if len(by_left) != len(rows):
        raise ValueError("Duplicate left candidate ID")
    owners = {}
    for row in rows:
        for match in row["matching_right_proposals"]:
            owners.setdefault(match["right_proposal_id"], set()).add(row["left_candidate_id"])
    unseen = set(by_left)
    groups = []
    while unseen:
        seed = min(unseen, key=lambda left_id: (by_left[left_id]["left_passage_time_s"], left_id))
        members = {seed}
        pending = [seed]
        while pending:
            left_id = pending.pop()
            for match in by_left[left_id]["matching_right_proposals"]:
                for other in owners[match["right_proposal_id"]] - members:
                    members.add(other)
                    pending.append(other)
        unseen -= members
        ordered = sorted(
            members, key=lambda left_id: (by_left[left_id]["left_passage_time_s"], left_id)
        )
        right_ids = sorted(
            {
                match["right_proposal_id"]
                for left_id in ordered
                for match in by_left[left_id]["matching_right_proposals"]
            }
        )
        first = by_left[ordered[0]]
        colour_directions = {
            (by_left[left_id]["colour_claim"], by_left[left_id]["direction"]) for left_id in ordered
        }
        if len(colour_directions) != 1:
            raise ValueError("Shared right proposal crosses colour or direction")
        kind = (
            "no_right_candidate"
            if not right_ids
            else "one_to_one_time_candidate"
            if len(ordered) == len(right_ids) == 1
            else "shared_one_right_candidate"
            if len(right_ids) == 1
            else "multiple_right_candidates"
        )
        groups.append(
            {
                "member_left_candidate_ids": ordered,
                "right_proposal_ids": right_ids,
                "colour_claim": first["colour_claim"],
                "direction": first["direction"],
                "observation_time_s": first["left_passage_time_s"],
                "observation_time_semantics": "first_left_candidate_passage",
                "first_left_passage_time_s": first["left_passage_time_s"],
                "last_left_passage_time_s": by_left[ordered[-1]]["left_passage_time_s"],
                "episode_kind": kind,
                "physical_throw_count_verified": False,
                "cross_view_physical_identity_verified": False,
            }
        )
    if right_proposals is not None:
        if interval_s is None or len(interval_s) != 2 or interval_s[0] >= interval_s[1]:
            raise ValueError("Right inventory requires a valid candidate interval")
        by_right = {row["proposal_id"]: row for row in right_proposals}
        if len(by_right) != len(right_proposals) or not set(owners) <= set(by_right):
            raise ValueError("Right inventory duplicate or missing matched ID")
        for right_id, right in by_right.items():
            t = right["passage_time_s"]
            if right_id in owners or not interval_s[0] <= t <= interval_s[1]:
                continue
            groups.append(
                {
                    "member_left_candidate_ids": [],
                    "right_proposal_ids": [right_id],
                    "colour_claim": right["colour_claim"],
                    "direction": right["direction"],
                    "observation_time_s": t,
                    "observation_time_semantics": "right_observed_motion_passage",
                    "first_left_passage_time_s": None,
                    "last_left_passage_time_s": None,
                    "episode_kind": "right_only_candidate",
                    "physical_throw_count_verified": False,
                    "cross_view_physical_identity_verified": False,
                }
            )
    groups.sort(
        key=lambda row: (
            row["observation_time_s"],
            row["member_left_candidate_ids"],
            row["right_proposal_ids"],
        )
    )
    for index, group in enumerate(groups, 1):
        group["episode_id"] = f"E{index:03d}"
    return groups
