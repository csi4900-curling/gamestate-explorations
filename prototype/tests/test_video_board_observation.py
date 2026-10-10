from collections import Counter
import json
from pathlib import Path

import cv2

from prototype.board_state_comparison import compare_board_observations
from prototype.video_board_observation import detect_board_stones, detect_overhead_house


FIXTURES = Path(__file__).parent / "fixtures"


def test_real_overhead_frame_detects_house_and_ten_coloured_stones():
    frame = cv2.imread(str(FIXTURES / "pwg2022-overhead-board.jpg"))
    house = detect_overhead_house(frame)
    assert house is not None
    assert house["delivery_side"] == "top"
    assert abs(house["center_px"][0] - 315) <= 5
    assert abs(house["center_px"][1] - 250) <= 5
    stones = detect_board_stones(frame, house)
    assert Counter(stone["colour"] for stone in stones) == {"red": 5, "yellow": 5}


def test_delivery_view_does_not_pass_overhead_house_check():
    frame = cv2.imread(str(FIXTURES / "pwg2022-delivery-view.jpg"))
    assert detect_overhead_house(frame) is None


def test_clear_video_board_matches_its_official_diagram():
    frame = cv2.imread(str(FIXTURES / "pwg2022-overhead-board.jpg"))
    house = detect_overhead_house(frame)
    stones = detect_board_stones(frame, house)
    path = (
        Path(__file__).resolve().parents[2]
        / "validation/official-shot-sequence/pwg2022-official-board-diagrams.json"
    )
    diagrams = json.loads(path.read_text())
    official = next(
        shot
        for game in diagrams["games"]
        for end in game["ends"]
        for shot in end["shots"]
        if shot["official_shot_id"] == "PREL000102-E07-S15"
    )
    comparison = compare_board_observations(
        stones, official["stones"], official_house_center_y=official["house_center_px"][1]
    )
    assert comparison["matched_count"] == 10
    assert comparison["max_matched_distance_house_radii"] < 0.08
