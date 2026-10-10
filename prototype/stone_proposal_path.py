"""Conservative same-view motion runs through sparse stone proposals."""

from math import dist


def first_visible_stability_onset(path, duration_s=5.0, pixel_radius=2.0):
    """Earliest observed sample staying within an image-space radius for a window."""
    for i, start in enumerate(path):
        window = [
            node
            for node in path[i:]
            if node["source_time_s"] <= start["source_time_s"] + duration_s
        ]
        if not window or window[-1]["source_time_s"] < start["source_time_s"] + duration_s:
            continue
        if all(
            dist(start["pixel_center"], node["pixel_center"]) <= pixel_radius for node in window
        ):
            return start["source_time_s"]
    return None


def select_single_colour_motion_run(
    rows,
    colour,
    view="right",
    max_gap_s=0.6,
    max_speed_m_s=3.5,
    reverse_tolerance_m=0.25,
    min_travel_m=2.0,
    min_samples=5,
):
    """Find a unique longest run with one same-colour proposal per sample.

    Geometry and colour only provide a provisional association. A missing or
    multiple same-colour proposal breaks a run; it is never interpolated.
    """
    if any(a["source_time_s"] >= b["source_time_s"] for a, b in zip(rows, rows[1:])):
        raise ValueError("Samples must be strictly increasing")
    runs = []
    current = []

    def flush():
        nonlocal current
        if current:
            runs.append(current)
            current = []

    for row in rows:
        candidates = [
            p
            for p in row["views"][view]["proposals"]
            if p["colour"] == colour and p["ground_position_m"] is not None
        ]
        if len(candidates) != 1:
            flush()
            continue
        proposal = candidates[0]
        node = {
            "source_time_s": row["source_time_s"],
            "pixel_center": proposal["pixel_center"],
            "ground_position_m": proposal["ground_position_m"],
            "same_colour_candidate_count": 1,
        }
        if current:
            previous = current[-1]
            dt = node["source_time_s"] - previous["source_time_s"]
            distance = dist(node["ground_position_m"], previous["ground_position_m"])
            reverse = node["ground_position_m"][1] - previous["ground_position_m"][1]
            if dt > max_gap_s or distance > max_speed_m_s * dt or reverse > reverse_tolerance_m:
                flush()
        current.append(node)
    flush()
    eligible = []
    for run in runs:
        travel = dist(run[0]["ground_position_m"], run[-1]["ground_position_m"])
        if len(run) >= min_samples and travel >= min_travel_m:
            eligible.append((run, travel))
    if not eligible:
        return {"status": "no_supported_motion_run", "path": [], "candidate_run_count": len(runs)}
    longest = max(len(run) for run, _ in eligible)
    winners = [(run, travel) for run, travel in eligible if len(run) == longest]
    if len(winners) != 1:
        return {
            "status": "ambiguous_equal_length_motion_runs",
            "path": [],
            "candidate_run_count": len(runs),
            "equal_length_run_count": len(winners),
        }
    run, travel = winners[0]
    step_speeds = [
        dist(a["ground_position_m"], b["ground_position_m"])
        / (b["source_time_s"] - a["source_time_s"])
        for a, b in zip(run, run[1:])
    ]
    return {
        "status": "provisional_unique_same_colour_motion_run",
        "path": run,
        "sample_count": len(run),
        "first_observation_s": run[0]["source_time_s"],
        "last_observation_s": run[-1]["source_time_s"],
        "endpoint_displacement_m": travel,
        "first_step_speed_m_s": step_speeds[0],
        "last_step_speed_m_s": step_speeds[-1],
        "maximum_step_speed_m_s": max(step_speeds),
        "visible_stability_onset_s": first_visible_stability_onset(run),
        "visible_stability_rule": "First sampled point with all proposals within 2 px for the next 5 s; image-space observation, not exact physical stop time.",
        "candidate_run_count": len(runs),
        "release_time_observed": False,
        "physical_identity_verified": False,
        "metric_accuracy_verified": False,
        "simulation_ready": False,
    }


def select_far_entry_motion_path(
    rows,
    colour,
    view="right",
    max_gap_s=1.1,
    entry_y_threshold_m=12.0,
    forward_direction=-1,
    min_forward_step_m=0.3,
    max_speed_m_s=3.5,
    max_lateral_speed_m_s=1.2,
    max_forward_speed_change_m_s=0.75,
    min_samples=5,
    min_travel_m=2.0,
    allow_missing_samples=False,
    skip_status_required=None,
):
    """Follow a unique longest far-to-house moving path amid parked stones.

    Every selected step must move toward the house. Missing samples break the
    path. This isolates a moving phase but does not prove stone identity.
    """
    if any(a["source_time_s"] >= b["source_time_s"] for a, b in zip(rows, rows[1:])):
        raise ValueError("Samples must be strictly increasing")
    if forward_direction not in (-1, 1):
        raise ValueError("Forward direction must be -1 or 1")
    nodes = []
    by_sample = []
    for sample_i, row in enumerate(rows):
        indices = []
        for proposal in row["views"][view]["proposals"]:
            if proposal["colour"] != colour or proposal["ground_position_m"] is None:
                continue
            indices.append(len(nodes))
            nodes.append(
                {
                    "sample_i": sample_i,
                    "source_time_s": row["source_time_s"],
                    "pixel_center": proposal["pixel_center"],
                    "ground_position_m": proposal["ground_position_m"],
                    "same_colour_candidate_count": sum(
                        p["colour"] == colour for p in row["views"][view]["proposals"]
                    ),
                }
            )
        by_sample.append(indices)
    states_by_sample = []
    finished = []
    for sample_i, indices in enumerate(by_sample):
        current = {}
        for i in indices:
            node = nodes[i]
            paths = (
                [(i,)]
                if forward_direction * (node["ground_position_m"][1] - entry_y_threshold_m) <= 0
                else []
            )
            if sample_i:
                earlier_sample_indices = (
                    range(sample_i - 1, -1, -1) if allow_missing_samples else (sample_i - 1,)
                )
                for earlier_sample_i in earlier_sample_indices:
                    if node["source_time_s"] - rows[earlier_sample_i]["source_time_s"] > max_gap_s:
                        break
                    if (
                        earlier_sample_i < sample_i - 1
                        and skip_status_required is not None
                        and any(
                            rows[k].get("status") != skip_status_required
                            for k in range(earlier_sample_i + 1, sample_i)
                        )
                    ):
                        continue
                    for j in by_sample[earlier_sample_i]:
                        earlier = nodes[j]
                        dt = node["source_time_s"] - earlier["source_time_s"]
                        dx = node["ground_position_m"][0] - earlier["ground_position_m"][0]
                        forward = forward_direction * (
                            node["ground_position_m"][1] - earlier["ground_position_m"][1]
                        )
                        if (
                            dt > max_gap_s
                            or forward < min_forward_step_m
                            or dist(node["ground_position_m"], earlier["ground_position_m"])
                            > max_speed_m_s * dt
                            or abs(dx) > max_lateral_speed_m_s * dt
                        ):
                            continue
                        for prior_path in states_by_sample[earlier_sample_i].get(j, []):
                            if len(prior_path) >= 2:
                                before = nodes[prior_path[-2]]
                                earlier_dt = earlier["source_time_s"] - before["source_time_s"]
                                earlier_speed = (
                                    forward_direction
                                    * (
                                        earlier["ground_position_m"][1]
                                        - before["ground_position_m"][1]
                                    )
                                    / earlier_dt
                                )
                                if abs(forward / dt - earlier_speed) > max_forward_speed_change_m_s:
                                    continue
                            paths.append(prior_path + (i,))
            if len(paths) > 64:
                return {
                    "status": "ambiguous_far_entry_motion_paths",
                    "path": [],
                    "reason": "Candidate path enumeration limit exceeded",
                }
            current[i] = paths
            finished.extend(paths)
        states_by_sample.append(current)
    eligible = [
        path
        for path in finished
        if len(path) >= min_samples
        and dist(nodes[path[0]]["ground_position_m"], nodes[path[-1]]["ground_position_m"])
        >= min_travel_m
    ]
    if not eligible:
        return {
            "status": "no_supported_far_entry_motion_path",
            "path": [],
            "sample_count": len(rows),
            "same_colour_proposal_count": len(nodes),
        }
    best = max(map(len, eligible))
    winners = [path for path in eligible if len(path) == best]
    if len(winners) != 1:
        prefix = []
        for choices in zip(*winners):
            if len(set(choices)) != 1:
                break
            prefix.append(choices[0])
        return {
            "status": "ambiguous_far_entry_motion_paths",
            "path": [],
            "best_path_sample_count": best,
            "winner_count": min(2, len(winners)),
            "shared_prefix": [
                {key: value for key, value in nodes[index].items() if key != "sample_i"}
                for index in prefix
            ],
            "shared_prefix_sample_count": len(prefix),
            "first_ambiguity_time_s": (
                nodes[winners[0][len(prefix)]]["source_time_s"] if len(prefix) < best else None
            ),
            "alternative_paths": [
                [
                    {key: value for key, value in nodes[index].items() if key != "sample_i"}
                    for index in option
                ]
                for option in winners[:2]
            ],
        }
    path = [
        {key: value for key, value in nodes[index].items() if key != "sample_i"}
        for index in winners[0]
    ]
    observation_gaps = [b["source_time_s"] - a["source_time_s"] for a, b in zip(path, path[1:])]
    skipped_samples = [
        nodes[b]["sample_i"] - nodes[a]["sample_i"] - 1 for a, b in zip(winners[0], winners[0][1:])
    ]
    return {
        "status": "provisional_unique_far_entry_motion_path",
        "path": path,
        "sample_count": len(path),
        "first_observation_s": path[0]["source_time_s"],
        "last_observation_s": path[-1]["source_time_s"],
        "endpoint_displacement_m": dist(
            path[0]["ground_position_m"], path[-1]["ground_position_m"]
        ),
        "frames_with_multiple_same_colour_candidates": sum(
            node["same_colour_candidate_count"] > 1 for node in path
        ),
        "unobserved_gap_count": sum(gap > 0 for gap in skipped_samples),
        "unobserved_sample_count": sum(skipped_samples),
        "largest_observation_gap_s": max(observation_gaps, default=0),
        "release_time_observed": False,
        "physical_identity_verified": False,
        "metric_accuracy_verified": False,
        "simulation_ready": False,
    }
