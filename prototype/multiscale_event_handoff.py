"""Uncertainty-preserving handoff from alternative camera-shot segmentations."""


def build_multiscale_handoff(baseline_events, augmented_events,
                             augmented_visual_evidence=None,
                             augmented_counter_screen=None):
    """Keep stable counter identities while retaining conflicting observations."""
    def counters(events):
        out = {}
        for event in events:
            key = event.get("counter_id")
            if key:
                if key in out:
                    raise ValueError(f"Duplicate counter ID: {key}")
                out[key] = event
        return out

    old, new = counters(baseline_events), counters(augmented_events)
    counter_rows = []
    for counter_id in sorted(set(old) | set(new)):
        alternatives = []
        for segmentation, index in (("conservative_hard_cuts", old),
                                    ("isolated_edit_augmented", new)):
            event = index.get(counter_id)
            if event:
                alternatives.append({"segmentation": segmentation,
                                     "candidate_id": event["candidate_id"],
                                     "camera_shot_id": event["shot_id"],
                                     "release_window_s": event["release_window_s"],
                                     "colour": event.get("colour"),
                                     "colour_status": event.get("colour_status"),
                                     "evidence_sources": event["evidence_sources"]})
        colours = [a["colour"] for a in alternatives]
        agreement = (len(alternatives) == 2 and colours[0] is not None and
                     colours[0] == colours[1])
        counter_rows.append({
            "counter_id": counter_id,
            "alternative_observations": alternatives,
            "colour": colours[0] if agreement else None,
            "colour_agreement": agreement,
            "release_window_agreement": (len(alternatives) == 2 and
                                         alternatives[0]["release_window_s"] ==
                                         alternatives[1]["release_window_s"]),
            "physical_throw_identity_verified": False,
            "exact_release_time_s": None,
            "exact_settle_time_s": None,
            "simulation_ready": False,
        })

    cues = {row["candidate_id"]: row for row in (augmented_visual_evidence or [])}
    if len(cues) != len(augmented_visual_evidence or []):
        raise ValueError("Duplicate augmented visual evidence candidate ID")
    augmented_visual_ids = {event["candidate_id"] for event in augmented_events
                            if not event.get("counter_id")}
    if augmented_visual_evidence is not None and set(cues) != augmented_visual_ids:
        raise ValueError("Augmented visual evidence candidate IDs differ")
    counterscreen = {row["candidate_id"]: row
                     for row in (augmented_counter_screen or [])}
    if len(counterscreen) != len(augmented_counter_screen or []):
        raise ValueError("Duplicate augmented counter-screen candidate ID")
    if augmented_counter_screen is not None and set(counterscreen) != augmented_visual_ids:
        raise ValueError("Augmented counter-screen candidate IDs differ")
    visual_rows = []
    for segmentation, events in (("conservative_hard_cuts", baseline_events),
                                 ("isolated_edit_augmented", augmented_events)):
        for event in events:
            if event.get("counter_id"):
                continue
            cue = cues.get(event["candidate_id"]) if segmentation == "isolated_edit_augmented" else None
            counter_context = (counterscreen.get(event["candidate_id"])
                               if segmentation == "isolated_edit_augmented" else None)
            visual_rows.append({
                "segmentation": segmentation,
                "candidate_id": event["candidate_id"],
                "camera_shot_id": event["shot_id"],
                "release_window_s": event["release_window_s"],
                "colour": event.get("colour"),
                "visual_evidence_pattern": cue["evidence_pattern"] if cue else None,
                "visual_evidence_status": "audited" if cue else "not_audited",
                "counter_consistency_status": (counter_context["status"]
                                               if counter_context else None),
                "counter_consistency_audited": counter_context is not None,
                "physical_throw_identity_verified": False,
                "potential_duplicate_or_split": True,
                "simulation_ready": False,
            })
    return {"counter_backed_hypotheses": counter_rows,
            "unmerged_visual_only_proposals": visual_rows,
            "counter_hypothesis_count": len(counter_rows),
            "unmerged_visual_proposal_count": len(visual_rows),
            "simulation_ready_count": 0,
            "limitations": [
                "Counter identity is broadcast evidence and is not an independent physical throw label.",
                "Conflicting colours or windows remain as alternatives; no majority vote is used.",
                "Visual-only proposals across segmentations are not automatically deduplicated.",
                "Visual cue patterns are diagnostics; neither missing cue disproves a throw.",
                "Counter consistency is broadcast evidence, not independent event truth.",
                "No exact release, settle, full game state, or physics simulation is established.",
            ]}
