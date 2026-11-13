from prototype.scripts.probe_latvia_end6_lower_cap_direction import link_lower_detections


def sample(time_s, red=(), yellow=()):
    return {
        "time_s": time_s,
        "lower_colour_proposals": {
            "red": [
                {"pixel": [x, y], "bbox": [x - 3, y - 3, 6, 6], "cap_area_px2": 18} for x, y in red
            ],
            "yellow": [
                {"pixel": [x, y], "bbox": [x - 3, y - 3, 6, 6], "cap_area_px2": 18}
                for x, y in yellow
            ],
        },
    }


def test_dense_image_links_keep_colour_and_direction_separate():
    rows = [
        sample(0, red=[(400, 300)], yellow=[(500, 240)]),
        sample(0.5, red=[(402, 286)], yellow=[(500, 253)]),
        sample(1, red=[(404, 270)], yellow=[(500, 267)]),
    ]
    tracks = link_lower_detections(rows)
    assert [(row["colour"], row["direction"]) for row in tracks] == [
        ("red", "upward"),
        ("yellow", "downward"),
    ]
    assert [len(row["points"]) for row in tracks] == [3, 3]
