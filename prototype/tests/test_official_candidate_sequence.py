import pytest

from prototype.official_candidate_sequence import align_official_sequence


def shot(number, team):
    return {"official_shot_id": f"S{number}", "team": team}


def candidate(number, colour):
    return {"candidate_id": f"C{number}", "colour": colour}


def test_exact_sequence_matches_and_wrong_colour_candidate_is_skipped():
    result = align_official_sequence(
        [candidate(1, "yellow"), candidate(2, "red"), candidate(3, "red"), candidate(4, "yellow")],
        [shot(1, "Y"), shot(2, "R"), shot(3, "Y")],
        {"Y": "yellow", "R": "red"},
        {"C2": "S2"},
    )
    assert [row["unique_official_shot_id"] for row in result["candidate_rows"]] == [
        "S1",
        "S2",
        None,
        "S3",
    ]
    assert result["candidate_rows"][2]["status"] == "skipped_in_every_optimum"


def test_duplicate_same_colour_remains_ambiguous():
    result = align_official_sequence(
        [candidate(1, "yellow"), candidate(2, "yellow")], [shot(1, "Y")], {"Y": "yellow"}, {}
    )
    assert result["optimal_path_count"] == 2
    assert all(row["status"] == "ambiguous_optimal_alignment" for row in result["candidate_rows"])


def test_crossing_fixed_links_rejected():
    with pytest.raises(ValueError, match="chronology"):
        align_official_sequence(
            [candidate(1, "yellow"), candidate(2, "red")],
            [shot(1, "Y"), shot(2, "R")],
            {"Y": "yellow", "R": "red"},
            {"C1": "S2", "C2": "S1"},
        )


def test_independent_colour_correction_can_recover_a_previously_skipped_candidate():
    official = [shot(1, "Y"), shot(2, "R"), shot(3, "Y")]
    fixed = {"C1": "S1", "C2": "S2"}
    original = align_official_sequence(
        [candidate(1, "yellow"), candidate(2, "red"), candidate(3, "red")],
        official,
        {"Y": "yellow", "R": "red"},
        fixed,
    )
    corrected = align_official_sequence(
        [candidate(1, "yellow"), candidate(2, "red"), candidate(3, "yellow")],
        official,
        {"Y": "yellow", "R": "red"},
        fixed,
    )
    assert original["candidate_rows"][2]["status"] == "skipped_in_every_optimum"
    assert corrected["candidate_rows"][2]["unique_official_shot_id"] == "S3"
