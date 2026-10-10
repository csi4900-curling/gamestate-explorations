from prototype.stable_image_cap_observation import stable_cap_centers


def test_requires_repeated_position_across_all_frames():
    frames = [{"source_time_s": t, "caps": [
        {"colour": "yellow", "pixel_center": [100 + shift, 200]},
        {"colour": "yellow", "pixel_center": [300 + 30 * index, 300]},
    ]} for index, (t, shift) in enumerate(((0, 0), (5, 2), (10, 1)))]
    stable = stable_cap_centers(frames)
    assert len(stable) == 1
    assert stable[0]["median_pixel_center"] == [101, 200]


def test_missing_middle_frame_cannot_be_stable():
    frames = [
        {"source_time_s": 0, "caps": [{"colour": "yellow", "pixel_center": [100, 200]}]},
        {"source_time_s": 5, "caps": []},
        {"source_time_s": 10, "caps": [{"colour": "yellow", "pixel_center": [100, 200]}]},
    ]
    assert stable_cap_centers(frames) == []
