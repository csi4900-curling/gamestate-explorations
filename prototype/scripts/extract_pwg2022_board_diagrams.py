"""Extract source-linked post-shot diagram stone positions from official PDF."""

from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

import cv2
import numpy as np
import pymupdf


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.official_board_diagram import extract_stone_symbols, house_center_y

REFERENCE = ROOT / "validation/official-shot-sequence/pwg2022-official-shot-ledger.json"
PDF = ROOT / "validation/official-shot-sequence/PWG2022_ResultsBook.pdf"
OUTPUT = ROOT / "validation/official-shot-sequence/pwg2022-official-board-diagrams.json"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def shot_images(page):
    images = []
    for item in page.get_images(full=True):
        if item[2:4] != (300, 600):
            continue
        for rect in page.get_image_rects(item[0]):
            images.append((rect.y0, rect.x0, item[0], rect))
    return sorted(images)


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first board-diagram extraction")
    reference = json.loads(REFERENCE.read_text())
    if reference["official_pdf_sha256"] != digest(PDF):
        raise ValueError("Official PDF differs from shot-order ledger")
    document = pymupdf.open(PDF)
    games = []
    for game in reference["games"]:
        ends = []
        for end in game["ends"]:
            page = document[end["pdf_page"] - 1]
            images = shot_images(page)
            if len(images) != end["shot_count"]:
                raise ValueError(
                    f"Diagram count differs from official shots on page {end['pdf_page']}"
                )
            rows = []
            previous_strict_count = None
            for shot, (_, _, xref, rect) in zip(end["shots"], images):
                raw = document.extract_image(xref)["image"]
                image = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
                stones = extract_stone_symbols(image)
                house_y = house_center_y(image)
                counts = Counter(row["colour"] for row in stones)
                strict_count = sum(not row["near_diagram_edge"] for row in stones)
                flags = []
                if len(stones) > shot["shot_number"]:
                    flags.append("more_diagram_stones_than_deliveries")
                if any(counts[colour] > 8 for colour in ("red", "yellow")):
                    flags.append("more_than_eight_stones_of_one_colour")
                if previous_strict_count is not None and strict_count > previous_strict_count + 1:
                    flags.append("strict_diagram_occupancy_gained_multiple")
                if any(row["near_diagram_edge"] for row in stones):
                    flags.append("edge_symbol_play_status_uncertain")
                if any(row["low_fill_margin"] for row in stones):
                    flags.append("low_fill_margin_needs_review")
                rows.append(
                    {
                        "official_shot_id": shot["official_shot_id"],
                        "diagram_image_xref": xref,
                        "diagram_image_sha256": hashlib.sha256(raw).hexdigest(),
                        "diagram_pdf_rect": [round(value, 3) for value in rect],
                        "house_center_px": [150, house_y],
                        "delivery_side": "top" if house_y == 440 else "bottom",
                        "stone_counts": {colour: counts[colour] for colour in ("red", "yellow")},
                        "stones": stones,
                        "review_flags": flags,
                    }
                )
                previous_strict_count = strict_count
            ends.append(
                {
                    "end": end["end"],
                    "pdf_page": end["pdf_page"],
                    "diagram_count": len(rows),
                    "shots": rows,
                }
            )
        games.append(
            {
                "official_game_code": game["official_game_code"],
                "source_video_sha256": game["source_video_sha256"],
                "ends": ends,
            }
        )
    shots = [shot for game in games for end in game["ends"] for shot in end["shots"]]
    flags = Counter(flag for shot in shots for flag in shot["review_flags"])
    output = {
        "status": "official_pdf_diagram_occupancy_not_verified_video_game_state",
        "official_pdf_sha256": digest(PDF),
        "shot_ledger_sha256": digest(REFERENCE),
        "extractor_code_sha256": digest(ROOT / "prototype/official_board_diagram.py"),
        "runner_sha256": digest(Path(__file__)),
        "diagram_image_size_px": [300, 600],
        "supported_house_centers_px": [[150, 160], [150, 440]],
        "house_outer_radius_px": 120,
        "shot_diagram_count": len(shots),
        "detected_stone_symbol_count": sum(len(shot["stones"]) for shot in shots),
        "review_flag_counts": dict(flags),
        "games": games,
        "limitations": [
            "These positions come from official post-shot diagrams, not tracked stones in video; they cannot establish throw release times or event F1.",
            "Filled colour symbols are selected by circle and palette evidence; thin outlines from prior positions are intended to be excluded.",
            "Near-edge symbols can represent boundary/out-of-play bookkeeping or partial stones; retain their uncertainty.",
            "Overlapping symbols and low-fill circles may be missed or merged; transition and fill flags identify cases requiring review.",
            "House-radius coordinates are unitless diagram coordinates, not calibrated physical metres or 3D trajectories.",
        ],
    }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n")
    print(
        output["shot_diagram_count"],
        output["detected_stone_symbol_count"],
        output["review_flag_counts"],
    )


if __name__ == "__main__":
    main()
