from cap_fragment_merge import merge_cap_fragments


def component(area, center, box):
    return {"area_px2": area, "centroid_px_1080": center,
            "bbox_xywh_px_1080": box}


def test_adjacent_small_handle_fragment_merges():
    parts = [component(199, [1441.452, 498.382], [1424, 490, 40, 14]),
             component(29.5, [1444.175, 485.701], [1440, 484, 10, 6])]
    result = merge_cap_fragments(parts)
    assert len(result) == 1
    assert result[0]["merged_source_component_indices"] == [0, 1]
    assert result[0]["bbox_xywh_px_1080"] == [1424, 484, 40, 20]


def test_distant_or_equal_sized_caps_remain_separate():
    parts = [component(199, [1441, 498], [1424, 490, 40, 14]),
             component(30, [1490, 490], [1485, 484, 10, 7]),
             component(170, [1443, 484], [1438, 478, 12, 8])]
    result = merge_cap_fragments(parts)
    assert len(result) == 3
    assert all(len(row["merged_source_component_indices"]) == 1 for row in result)


def test_ambiguous_many_to_one_fragment_is_not_merged():
    parts = [component(199, [1441, 498], [1424, 490, 40, 14]),
             component(30, [1440, 486], [1436, 484, 10, 6]),
             component(25, [1450, 486], [1446, 484, 10, 6])]
    result = merge_cap_fragments(parts)
    assert len(result) == 3
