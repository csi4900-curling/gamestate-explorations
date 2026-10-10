"""Extract Korea–China post-shot board diagrams from official PDF."""

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
from prototype.scripts.extract_pwg2022_board_diagrams import shot_images

REFERENCE = ROOT / "validation/official-shot-sequence/pwg2022-korea-china-official-ledger.json"
PDF = ROOT / "validation/official-shot-sequence/PWG2022_ResultsBook.pdf"
OUTPUT = ROOT / "validation/official-shot-sequence/pwg2022-korea-china-official-boards.json"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first official board extraction")
    reference = json.loads(REFERENCE.read_text())
    if reference["official_pdf_sha256"] != digest(PDF):
        raise ValueError("Different PDF from official shot ledger")
    document = pymupdf.open(PDF)
    ends = []
    for end in reference["ends"]:
        page = document[end["pdf_page"] - 1]
        images = shot_images(page)
        if len(images) != end["shot_count"]:
            raise ValueError(f"Diagram count differs on page {end['pdf_page']}")
        rows = []
        previous_strict = None
        for shot, (_, _, xref, rect) in zip(end["shots"], images):
            raw = document.extract_image(xref)["image"]
            image = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
            stones = extract_stone_symbols(image)
            house_y = house_center_y(image)
            counts = Counter(row["colour"] for row in stones)
            strict = sum(not row["near_diagram_edge"] for row in stones)
            flags = []
            if len(stones) > shot["shot_number"]:
                flags.append("more_diagram_stones_than_deliveries")
            if any(counts[colour] > 8 for colour in ("red", "yellow")):
                flags.append("more_than_eight_stones_of_one_colour")
            if previous_strict is not None and strict > previous_strict + 1:
                flags.append("strict_diagram_occupancy_gained_multiple")
            if any(row["near_diagram_edge"] for row in stones):
                flags.append("edge_symbol_play_status_uncertain")
            if any(row["low_fill_margin"] for row in stones):
                flags.append("low_fill_margin_needs_review")
            rows.append({"official_shot_id": shot["official_shot_id"],
                         "diagram_image_xref": xref,
                         "diagram_image_sha256": hashlib.sha256(raw).hexdigest(),
                         "diagram_pdf_rect": [round(value, 3) for value in rect],
                         "house_center_px": [150, house_y],
                         "delivery_side": "top" if house_y == 440 else "bottom",
                         "stone_counts": {colour: counts[colour] for colour in ("red", "yellow")},
                         "stones": stones, "review_flags": flags})
            previous_strict = strict
        ends.append({"end": end["end"], "pdf_page": end["pdf_page"],
                     "diagram_count": len(rows), "shots": rows})
    all_shots = [shot for end in ends for shot in end["shots"]]
    flags = Counter(flag for shot in all_shots for flag in shot["review_flags"])
    output = {
        "status": "independent_official_pdf_board_diagrams_without_video_timestamps",
        "official_pdf_sha256": digest(PDF),
        "shot_ledger_sha256": digest(REFERENCE),
        "source_video_sha256": reference["source_video_sha256"],
        "extractor_code_sha256": digest(ROOT / "prototype/official_board_diagram.py"),
        "runner_sha256": digest(Path(__file__)),
        "shot_diagram_count": len(all_shots),
        "detected_stone_symbol_count": sum(len(shot["stones"]) for shot in all_shots),
        "review_flag_counts": dict(flags),
        "ends": ends,
        "limitations": ["PDF diagrams provide post-shot 2D positions only; they are not tracked video states or physical throw timestamps."],
    }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n")
    print(output["shot_diagram_count"], output["detected_stone_symbol_count"],
          output["review_flag_counts"])


if __name__ == "__main__":
    main()
