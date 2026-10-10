"""Merge only geometrically adjacent small colour-cap fragments for probing."""

from math import dist


def _compatible(
    big,
    small,
    *,
    max_area_ratio,
    max_vertical_gap_px,
    min_small_horizontal_overlap,
    max_center_distance_px,
):
    if small["area_px2"] > max_area_ratio * big["area_px2"]:
        return False
    bx, by, bw, bh = big["bbox_xywh_px_1080"]
    sx, sy, sw, sh = small["bbox_xywh_px_1080"]
    overlap = max(0, min(bx + bw, sx + sw) - max(bx, sx))
    if overlap < min_small_horizontal_overlap * sw:
        return False
    gap = max(0, by - (sy + sh), sy - (by + bh))
    if gap > max_vertical_gap_px:
        return False
    return dist(big["centroid_px_1080"], small["centroid_px_1080"]) <= max_center_distance_px


def merge_cap_fragments(
    components,
    *,
    max_area_ratio=0.25,
    max_vertical_gap_px=3,
    min_small_horizontal_overlap=0.5,
    max_center_distance_px=20,
):
    """Merge unique big/small bbox neighbors; leave competing pairs untouched.

    This only repairs a colour-mask split. It cannot prove one physical stone.
    """
    if any(row["area_px2"] <= 0 for row in components):
        raise ValueError("Component areas must be positive")
    pairs = []
    for big_i, big in enumerate(components):
        for small_i, small in enumerate(components):
            if big_i == small_i or big["area_px2"] <= small["area_px2"]:
                continue
            if _compatible(
                big,
                small,
                max_area_ratio=max_area_ratio,
                max_vertical_gap_px=max_vertical_gap_px,
                min_small_horizontal_overlap=min_small_horizontal_overlap,
                max_center_distance_px=max_center_distance_px,
            ):
                pairs.append((big_i, small_i))
    degree = {i: sum(i in pair for pair in pairs) for i in range(len(components))}
    merges = {big: small for big, small in pairs if degree[big] == degree[small] == 1}
    consumed = set(merges.values())
    result = []
    for i, row in enumerate(components):
        if i in consumed:
            continue
        if i not in merges:
            result.append({**row, "merged_source_component_indices": [i]})
            continue
        j = merges[i]
        other = components[j]
        a, b = row["area_px2"], other["area_px2"]
        x0 = min(row["bbox_xywh_px_1080"][0], other["bbox_xywh_px_1080"][0])
        y0 = min(row["bbox_xywh_px_1080"][1], other["bbox_xywh_px_1080"][1])
        x1 = max(
            row["bbox_xywh_px_1080"][0] + row["bbox_xywh_px_1080"][2],
            other["bbox_xywh_px_1080"][0] + other["bbox_xywh_px_1080"][2],
        )
        y1 = max(
            row["bbox_xywh_px_1080"][1] + row["bbox_xywh_px_1080"][3],
            other["bbox_xywh_px_1080"][1] + other["bbox_xywh_px_1080"][3],
        )
        result.append(
            {
                "area_px2": a + b,
                "centroid_px_1080": [
                    round(
                        (a * row["centroid_px_1080"][k] + b * other["centroid_px_1080"][k])
                        / (a + b),
                        3,
                    )
                    for k in (0, 1)
                ],
                "bbox_xywh_px_1080": [x0, y0, x1 - x0, y1 - y0],
                "merged_source_component_indices": [i, j],
            }
        )
    return result
