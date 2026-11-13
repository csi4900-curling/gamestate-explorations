import cv2
from pathlib import Path

from prototype.video_board_observation_v2 import detect_overhead_house


FIXTURES = Path(__file__).parent / "fixtures"


def test_component_house_recovers_clear_video_frame():
    frame = cv2.imread(str(FIXTURES / "pwg2022-overhead-board.jpg"))
    house = detect_overhead_house(frame)
    assert house is not None
    assert house["delivery_side"] == "top"
    assert abs(house["center_px"][0] - 314) <= 2
    assert abs(house["center_px"][1] - 250) <= 2
    assert house["annulus_support"]["supported_angle_bins"] >= 60


def test_component_house_rejects_delivery_view():
    frame = cv2.imread(str(FIXTURES / "pwg2022-delivery-view.jpg"))
    assert detect_overhead_house(frame) is None
