from prototype.multiscale_event_handoff import build_multiscale_handoff


def event(candidate, counter, window, colour):
    return {"candidate_id": candidate, "counter_id": counter,
            "shot_id": candidate, "release_window_s": window,
            "colour": colour, "colour_status": "resolved" if colour else "unresolved",
            "evidence_sources": ["visual_origin"]}


def test_colour_conflict_stays_unresolved_and_new_visual_is_separate():
    out = build_multiscale_handoff(
        [event("T1", "B1", [10, 20], "yellow")],
        [event("T2", "B1", [10, 15], None),
         event("T3", None, [15, 20], "red")])
    row = out["counter_backed_hypotheses"][0]
    assert row["colour"] is None
    assert not row["colour_agreement"]
    assert not row["release_window_agreement"]
    assert out["unmerged_visual_proposal_count"] == 1
    assert not row["simulation_ready"]


def test_stable_colour_can_pass_without_claiming_physical_identity():
    out = build_multiscale_handoff(
        [event("T1", "B1", [10, 20], "red")],
        [event("T2", "B1", [12, 20], "red")])
    row = out["counter_backed_hypotheses"][0]
    assert row["colour"] == "red"
    assert row["colour_agreement"]
    assert not row["physical_throw_identity_verified"]


def test_augmented_visual_evidence_is_attached_without_acceptance():
    visual = event("T3", None, [15, 20], "red")
    out = build_multiscale_handoff([], [visual], [{
        "candidate_id": "T3", "evidence_pattern": "neither_cue"}], [{
            "candidate_id": "T3", "status": "counter_state_gap_or_reset"}])
    row = out["unmerged_visual_only_proposals"][0]
    assert row["visual_evidence_pattern"] == "neither_cue"
    assert row["counter_consistency_status"] == "counter_state_gap_or_reset"
    assert row["potential_duplicate_or_split"]
    assert not row["simulation_ready"]
