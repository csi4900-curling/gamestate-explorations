"""Extract coloured stone symbols from official 300×600 shot diagrams."""

import cv2
import numpy as np


DIAGRAM_SIZE = (300, 600)
HOUSE_RADIUS_PX = 120
STONE_BGR = {"red": (41, 46, 238), "yellow": (55, 224, 245)}
HOUSE_PINK_BGR = (198, 198, 250)


def house_center_y(image):
    if image.shape != (600, 300, 3):
        raise ValueError("Expected 300×600 BGR shot diagram")
    pink = np.max(np.abs(image.astype(np.int16) - np.asarray(HOUSE_PINK_BGR)), axis=2) < 10
    if np.count_nonzero(pink) < 1000:
        raise ValueError("Missing official house circle")
    center = float(np.mean(np.flatnonzero(np.any(pink, axis=1))))
    if abs(center - 160) < 8:
        return 160
    if abs(center - 440) < 8:
        return 440
    raise ValueError(f"Unexpected house centre at y={center:.1f}")


def disc_fill_score(image, x, y, colour, *, radius=7, colour_tolerance=20):
    if colour not in STONE_BGR:
        raise ValueError("Unsupported stone colour")
    x0, x1 = max(0, x - radius), min(image.shape[1], x + radius + 1)
    y0, y1 = max(0, y - radius), min(image.shape[0], y + radius + 1)
    patch = image[y0:y1, x0:x1].astype(np.int16)
    yy, xx = np.mgrid[y0:y1, x0:x1]
    disc = (xx - x) ** 2 + (yy - y) ** 2 <= radius**2
    match = np.max(np.abs(patch - np.asarray(STONE_BGR[colour])), axis=2) < colour_tolerance
    return int(np.count_nonzero(match & disc))


def extract_stone_symbols(image, *, min_fill_score=65):
    """Return filled red/yellow circles, excluding top and bottom stone racks.

    Thin outline ghosts from the previous shot normally fail the fill test.
    Edge-adjacent symbols remain flagged because crop and play status are less
    certain there. The result is diagram occupancy, not legal-game adjudication.
    """
    if image.shape != (600, 300, 3):
        raise ValueError("Expected 300×600 BGR shot diagram")
    house_y = house_center_y(image)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    found = cv2.HoughCircles(
        gray[40:580],
        cv2.HOUGH_GRADIENT,
        dp=1,
        minDist=10,
        param1=100,
        param2=9,
        minRadius=6,
        maxRadius=9,
    )
    stones = []
    if found is None:
        return stones
    yy, xx = np.mgrid[-7:8, -7:8]
    kernel = ((xx**2 + yy**2) <= 49).astype(np.float32)
    scores = {}
    for colour, bgr in STONE_BGR.items():
        mask = np.max(np.abs(image.astype(np.int16) - np.asarray(bgr)), axis=2) < 20
        scores[colour] = cv2.filter2D(mask.astype(np.float32), -1, kernel)
    proposals = []
    for x_raw, y_raw, radius in found[0]:
        x, y = round(float(x_raw)), round(float(y_raw)) + 40
        x0, x1 = max(0, x - 8), min(300, x + 9)
        y0, y1 = max(40, y - 8), min(580, y + 9)
        values = []
        for colour, score_map in scores.items():
            crop = score_map[y0:y1, x0:x1]
            offset_y, offset_x = np.unravel_index(np.argmax(crop), crop.shape)
            values.append(
                (
                    round(float(crop[offset_y, offset_x])),
                    colour,
                    x0 + int(offset_x),
                    y0 + int(offset_y),
                )
            )
        score, colour, x, y = max(values)
        if score < min_fill_score:
            continue
        proposals.append(
            {
                "colour": colour,
                "diagram_pixel": [x, y],
                "house_radius_coordinates": [
                    round((x - 150) / HOUSE_RADIUS_PX, 4),
                    round((y - house_y) * (1 if house_y == 440 else -1) / HOUSE_RADIUS_PX, 4),
                ],
                "fill_score_px": score,
                "hough_radius_px": round(float(radius), 2),
                "near_diagram_edge": x < 8 or x > 292 or y < 48 or y > 572,
                "low_fill_margin": score < 85,
            }
        )
    for proposal in sorted(proposals, key=lambda row: -row["fill_score_px"]):
        x, y = proposal["diagram_pixel"]
        if all(
            (x - other["diagram_pixel"][0]) ** 2 + (y - other["diagram_pixel"][1]) ** 2 >= 10**2
            for other in stones
        ):
            stones.append(proposal)
    return sorted(
        stones, key=lambda row: (row["colour"], row["diagram_pixel"][1], row["diagram_pixel"][0])
    )
