"""Project official diagram stones into a detected video house field of view."""


def official_visibility(stones, *, official_house_center_y, video_house,
                        frame_size=(640, 360), stone_margin_px=10):
    if official_house_center_y not in (160, 440):
        raise ValueError("Unknown official diagram orientation")
    delivery_side = video_house["delivery_side"]
    if delivery_side not in ("top", "bottom"):
        raise ValueError("Known video delivery side required")
    official_lateral_sign = -1 if official_house_center_y == 160 else 1
    video_sign = 1 if delivery_side == "top" else -1
    cx, cy = video_house["center_px"]
    radius = video_house["outer_radius_px"]
    width, height = frame_size
    visible, outside = [], []
    for index, stone in enumerate(stones):
        lateral, longitudinal = stone["house_radius_coordinates"]
        x = cx + video_sign * official_lateral_sign * lateral * radius
        y = cy + video_sign * longitudinal * radius
        result = {"official_index": index, "colour": stone["colour"],
                  "projected_pixel": [round(x, 1), round(y, 1)]}
        if (stone_margin_px <= x < width - stone_margin_px
                and stone_margin_px <= y < height - stone_margin_px):
            visible.append(result)
        else:
            outside.append(result)
    return {"in_frame": visible, "outside_or_edge": outside,
            "in_frame_count": len(visible),
            "outside_or_edge_count": len(outside)}
