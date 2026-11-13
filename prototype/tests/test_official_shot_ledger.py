import pytest

from prototype.official_shot_ledger import parse_shot_page


def page(shots):
    return (
        "Game - Shot by Shot\n"
        "CAN - Canada 7 + X (this end) = 7\n"
        "End 8\n"
        "CHN - China 3 + X (this end) = 3\n" + shots
    )


def test_parses_through_shot_and_annotations_without_dropping_delivery():
    text = page(
        "Draw\n100%\n↻\nCAN: A\n1\n"
        "Front\n50%\n↺\nCHN: B\nTime-out\n2\n"
        "Through\n-\nCAN: A\nDid not pass the hogline\n3\n"
    )
    parsed = parse_shot_page(text, ("CAN", "CHN"))
    assert parsed["shot_count"] == 3
    assert parsed["header_team_order"] == ["CAN", "CHN"]
    assert parsed["team_scores"]["CAN"]["this_end"] == "X"
    assert parsed["shots"][1]["notes"] == ["Time-out"]
    assert parsed["shots"][2]["shot_type"] == "Through"
    assert parsed["shots"][2]["evaluation_percent"] is None
    assert parsed["shots"][2]["rotation"] is None


def test_rejects_missing_official_shot_number_and_non_alternation():
    with pytest.raises(ValueError, match="contiguous"):
        parse_shot_page(page("Draw\n100%\n↻\nCAN: A\n2\n"), ("CAN", "CHN"))
    with pytest.raises(ValueError, match="alternate"):
        parse_shot_page(
            page("Draw\n100%\n↻\nCAN: A\n1\nDraw\n100%\n↻\nCAN: A\n2\n"), ("CAN", "CHN")
        )
