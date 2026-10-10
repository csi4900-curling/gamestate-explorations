from prototype.scripts.compare_latvia_right_association_variants import compare


def row(track_id, time_s, colour="red", direction="negative_y"):
    return {"raw_track_id": track_id, "passage": {"time_s": time_s},
            "colour_claim": colour, "direction": direction}


def test_matching_keeps_two_valid_pairs_when_nearest_first_would_keep_one():
    old = [row("old0", 0), row("old8", 8)]
    new = [row("new7", 7), row("new15", 15)]
    result = compare(old, new)
    assert result["temporal_pair_count"] == 2
    assert {(x["left_raw_track_id"], x["right_raw_track_id"])
            for x in result["pairs"]} == {("old0", "new7"), ("old8", "new15")}


def test_colour_and_direction_mismatch_remain_unpaired():
    old = [row("old", 100)]
    new = [row("yellow", 100, colour="yellow"),
           row("reverse", 100, direction="positive_y")]
    result = compare(old, new)
    assert result["temporal_pair_count"] == 0
    assert [x["raw_track_id"] for x in result["left_unpaired"]] == ["old"]
    assert {x["raw_track_id"] for x in result["right_unpaired"]} == {
        "yellow", "reverse"}
