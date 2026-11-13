from prototype.release_colour_review import classify_release_colour


def test_unique_release_cue_can_flag_candidate_colour_conflict():
    result = classify_release_colour([{"colour": "yellow"}], "yellow", "red")
    assert result == {
        "status": "unique_shot_scoped_release_colour_cue",
        "release_colour": "yellow",
        "receiving_colour_relation": "agrees",
        "candidate_colour_relation": "conflicts",
    }


def test_receiving_colour_conflict_is_kept_explicit():
    result = classify_release_colour([{"colour": "yellow"}], "red")
    assert result["receiving_colour_relation"] == "conflicts"


def test_no_or_multiple_passages_abstain():
    for passages in ([], [{"colour": "red"}, {"colour": "red"}]):
        result = classify_release_colour(passages, "red")
        assert result["status"] == "abstain_no_unique_release_cue"
        assert result["release_colour"] is None
