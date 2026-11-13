from image_space_stone_cluster import stable_image_caps


def test_two_same_colour_caps_remain_separate_and_transient_drops():
    frames = []
    for t, drift in ((0, 0), (4, 1), (8, -1), (12, 0)):
        candidates = [
            {"colour": "red", "pixel": [100 + drift, 200], "patch_score": 0.7},
            {"colour": "red", "pixel": [400 + drift, 200], "patch_score": 0.6},
            {"colour": "yellow", "pixel": [300, 310 + drift], "patch_score": 1.0},
        ]
        if t == 4:
            candidates.append({"colour": "yellow", "pixel": [50, 50], "patch_score": 0.2})
        frames.append({"time_s": t, "candidates": candidates})
    result = stable_image_caps(frames)
    assert [(row["colour"], row["pixel_center"]) for row in result] == [
        ("red", [100.0, 200.0]),
        ("red", [400.0, 200.0]),
        ("yellow", [300.0, 310.0]),
    ]
    assert all(row["physical_stone_identity"] is None for row in result)
