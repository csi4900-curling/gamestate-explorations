"""Extract the official Canada–Norway 2022 shot order without video timing."""

import hashlib
import json
from pathlib import Path
import sys

import pymupdf

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.official_shot_ledger import parse_shot_page
from prototype.scripts.extract_pwg2022_shot_ledger import header_icon_evidence

PDF = ROOT / "validation/official-shot-sequence/PWG2022_ResultsBook.pdf"
VIDEO = ROOT / "validation/throw-event-benchmark/paralympics-2022-canada-norway/source.mp4"
OUTPUT = ROOT / "validation/official-shot-sequence/pwg2022-canada-norway-official-ledger.json"
CODE = "PREL001501"
TEAMS = ("CAN", "NOR")


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first official extraction")
    pages, ends, colours = [], [], None
    for index, page in enumerate(pymupdf.open(PDF)):
        text = page.get_text()
        if CODE not in text:
            continue
        if "Game Results" in text:
            pages.append(index + 1)
        if "Game - Shot by Shot" in text:
            row = parse_shot_page(text, TEAMS)
            icon_colours, _ = header_icon_evidence(page)
            mapping = dict(zip(row["header_team_order"], icon_colours))
            if colours is not None and colours != mapping:
                raise ValueError("Official team handle colours changed")
            colours = mapping
            row["pdf_page"] = index + 1
            for shot in row["shots"]:
                shot["official_shot_id"] = f"{CODE}-E{row['end']:02}-S{shot['shot_number']:02}"
            ends.append(row)
    ends.sort(key=lambda row: row["end"])
    if pages != [129] or [row["pdf_page"] for row in ends] != list(range(130, 138)):
        raise ValueError("Unexpected official Canada–Norway PDF pages")
    if [row["end"] for row in ends] != list(range(1, 9)) or any(row["shot_count"] != 16 for row in ends):
        raise ValueError("Unexpected official Canada–Norway shot sequence")
    result = {
        "status": "independent_official_shot_order_without_video_timestamps",
        "official_game_code": CODE,
        "teams": list(TEAMS),
        "team_handle_colours": colours,
        "official_pdf_url": "https://curlit.com/PDF/PWG2022_ResultsBook.pdf",
        "official_pdf_sha256": digest(PDF),
        "source_video_url": "https://www.youtube.com/watch?v=EoSwgOcH71g",
        "source_video_sha256": digest(VIDEO),
        "result_pdf_page": pages[0],
        "shot_pdf_pages": [row["pdf_page"] for row in ends],
        "official_shot_count": sum(row["shot_count"] for row in ends),
        "parser_sha256": digest(ROOT / "prototype/official_shot_ledger.py"),
        "runner_sha256": digest(Path(__file__)),
        "ends": ends,
        "limitations": ["Published shots and colours are independent of video inference, but the PDF provides no video event or release timestamps."],
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print(result["official_game_code"], result["official_shot_count"], colours)


if __name__ == "__main__":
    main()
