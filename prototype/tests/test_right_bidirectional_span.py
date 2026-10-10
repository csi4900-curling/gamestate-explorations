"""Bidirectional proposals retain direction and observed time semantics."""

from right_bidirectional_span import bidirectional_spans


def track(track_id, ys, colour="red"):
    return {
        "track_id": track_id,
        "colour": colour,
        "points": [
            {
                "time_s": float(i),
                "pixel": [430.0, float(y)],
                "bbox": [424, y - 3, 12, 6],
                "cap_area_px2": 18,
            }
            for i, y in enumerate(ys)
        ],
    }


def test_detects_both_image_directions_without_calling_passage_release():
    rows = bidirectional_spans(
        [track("UP", [300, 280, 260, 230]), track("DOWN", [180, 205, 235, 265])]
    )
    by_id = {row["raw_track_id"]: row for row in rows}
    assert by_id["UP"]["direction"] == "negative_y"
    assert by_id["DOWN"]["direction"] == "positive_y"
    assert by_id["UP"]["passage"]["pixel"][1] == 270.0
    assert by_id["DOWN"]["passage"]["pixel"][1] == 210.0
    assert all(
        row["passage_kind"].endswith("not_fixed_line")
        and not row["physical_throw_identity_verified"]
        for row in rows
    )


def test_stationary_or_tall_first_blob_is_not_promoted():
    stationary = track("STATIC", [200, 202, 201, 205])
    tall = track("TALL", [180, 205, 235, 265])
    tall["points"][0]["bbox"] = [424, 177, 6, 12]
    assert bidirectional_spans([stationary, tall]) == []
