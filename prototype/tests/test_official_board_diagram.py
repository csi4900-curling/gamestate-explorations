import numpy as np
import pytest
import cv2
from pathlib import Path

from prototype.official_board_diagram import disc_fill_score, extract_stone_symbols, house_center_y


def test_fill_score_distinguishes_coloured_disc_from_thin_outline():
    image = np.full((600, 300, 3), 255, np.uint8)
    yy, xx = np.mgrid[0:600, 0:300]
    filled = (xx - 100) ** 2 + (yy - 200) ** 2 <= 7**2
    outline = ((xx - 200) ** 2 + (yy - 200) ** 2 <= 7**2) & (
        (xx - 200) ** 2 + (yy - 200) ** 2 >= 6**2
    )
    image[filled] = (41, 46, 238)
    image[outline] = (41, 46, 238)
    assert disc_fill_score(image, 100, 200, "red") > 100
    assert disc_fill_score(image, 200, 200, "red") < 65


def test_rejects_wrong_diagram_shape():
    with pytest.raises(ValueError, match="300×600"):
        extract_stone_symbols(np.zeros((300, 600, 3), np.uint8))


def test_detects_both_official_house_orientations():
    image = np.full((600, 300, 3), 255, np.uint8)
    image[125:195, 110:190] = (198, 198, 250)
    assert house_center_y(image) == 160
    image[125:195, 110:190] = 255
    image[405:475, 110:190] = (198, 198, 250)
    assert house_center_y(image) == 440


def test_real_pdf_diagram_excludes_outline_ghosts():
    fixture = Path(__file__).parent / "fixtures/pwg2022-upper-house-ghosts.png"
    image = cv2.imread(str(fixture))
    stones = extract_stone_symbols(image)
    assert house_center_y(image) == 160
    assert len(stones) == 1
    assert stones[0]["colour"] == "red"
    assert abs(stones[0]["diagram_pixel"][0] - 185) <= 1
    assert abs(stones[0]["diagram_pixel"][1] - 269) <= 1


def test_real_pdf_diagram_recovers_button_stone_in_flipped_house():
    fixture = Path(__file__).parent / "fixtures/pwg2022-lower-house-button.png"
    image = cv2.imread(str(fixture))
    stones = extract_stone_symbols(image)
    assert house_center_y(image) == 440
    assert len(stones) == 1
    assert stones[0]["colour"] == "yellow"
    assert abs(stones[0]["house_radius_coordinates"][1]) < 0.1
