import json
from pathlib import Path

from prototype.board_visibility import official_visibility


def test_upper_house_diagram_rotates_into_top_delivery_video():
    stones = [
        {"colour": "red", "house_radius_coordinates": [1, -1]},
        {"colour": "yellow", "house_radius_coordinates": [0, -3]},
    ]
    house = {"center_px": [320, 220], "outer_radius_px": 100, "delivery_side": "top"}
    result = official_visibility(stones, official_house_center_y=160, video_house=house)
    assert result["in_frame"][0]["projected_pixel"] == [220, 120]
    assert result["outside_or_edge"][0]["projected_pixel"] == [320, -80]


def test_slovakia_zoom_excludes_some_official_stones():
    root = Path(__file__).resolve().parents[2]
    diagrams = json.loads(
        (
            root / "validation/official-shot-sequence/pwg2022-official-board-diagrams.json"
        ).read_text()
    )
    transfer = json.loads(
        (
            root / "validation/official-shot-sequence/pwg2022-video-board-transfer-v2.json"
        ).read_text()
    )
    official = next(
        shot
        for game in diagrams["games"]
        for end in game["ends"]
        for shot in end["shots"]
        if shot["official_shot_id"] == "PREL000103-E02-S15"
    )
    row = next(
        row for row in transfer["rows"] if row["official_shot_id"] == official["official_shot_id"]
    )
    result = official_visibility(
        official["stones"],
        official_house_center_y=official["house_center_px"][1],
        video_house=row["house"],
    )
    assert result["in_frame_count"] + result["outside_or_edge_count"] == 10
    assert result["outside_or_edge_count"] >= 3
