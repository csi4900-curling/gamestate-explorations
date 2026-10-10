"""Extract independent shot order for three recorded Beijing 2022 matches."""

import hashlib
import json
from pathlib import Path
import sys

import pymupdf
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.official_shot_ledger import parse_shot_page

PDF = ROOT / "validation/official-shot-sequence/PWG2022_ResultsBook.pdf"
OUTPUT = ROOT / "validation/official-shot-sequence/pwg2022-official-shot-ledger.json"
GAMES = (
    ("PREL000101", ("SWE", "SUI"), "ZJAMdkERdpE", "paralympics-2022-sweden-switzerland"),
    ("PREL000102", ("CAN", "CHN"), "qn9tHfcimlQ", "paralympics-2022-canada-china"),
    ("PREL000103", ("SVK", "USA"), "Ns12UZ5nlPk", "paralympics-2022-slovakia-usa"),
)


def digest(path):
    hash_value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hash_value.update(chunk)
    return hash_value.hexdigest()


def header_icon_evidence(page):
    """Read the two fixed PDF legend icons alongside the team score headers."""
    colours = []
    samples = []
    for x in (84, 335):
        pix = page.get_pixmap(matrix=pymupdf.Matrix(4, 4),
                              clip=pymupdf.Rect(x - 3, 151, x + 3, 157), alpha=False)
        rgb = np.frombuffer(pix.samples, dtype=np.uint8).reshape(-1, 3)
        median = np.median(rgb, axis=0)
        red, green, blue = median
        if red > 150 and red > green + 60 and red > blue + 60:
            colour = "red"
        elif red > 160 and green > 150 and blue < 130:
            colour = "yellow"
        else:
            raise ValueError(f"Unrecognized official team-colour icon on PDF page {page.number + 1}")
        colours.append(colour)
        samples.append([int(value) for value in median])
    if colours != ["red", "yellow"]:
        raise ValueError("Unexpected official team-colour icon order")
    return colours, samples


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first official extraction")
    document = pymupdf.open(PDF)
    games = []
    for code, teams, source_id, folder in GAMES:
        result_pages = []
        ends = []
        team_colours = None
        icon_samples = None
        for page_index, page in enumerate(document):
            text = page.get_text()
            if code not in text:
                continue
            if "Game Results" in text:
                result_pages.append(page_index + 1)
            if "Game - Shot by Shot" in text:
                row = parse_shot_page(text, teams)
                icon_colours, rgb_samples = header_icon_evidence(page)
                mapping = dict(zip(row["header_team_order"], icon_colours))
                if team_colours is not None and mapping != team_colours:
                    raise ValueError(f"Team handle colours changed within {code}")
                team_colours = mapping
                if icon_samples is None:
                    icon_samples = rgb_samples
                row["pdf_page"] = page_index + 1
                for shot in row["shots"]:
                    shot["official_shot_id"] = f"{code}-E{row['end']:02}-S{shot['shot_number']:02}"
                ends.append(row)
        if len(result_pages) != 1 or not ends:
            raise ValueError(f"Missing or duplicate official pages for {code}")
        ends.sort(key=lambda row: row["end"])
        if [row["end"] for row in ends] != list(range(1, len(ends) + 1)):
            raise ValueError(f"Noncontiguous official ends for {code}")
        source = ROOT / "validation/throw-event-benchmark" / folder / "source.mp4"
        games.append({
            "official_game_code": code,
            "teams": list(teams),
            "team_handle_colours": team_colours,
            "header_icon_median_rgb_on_first_shot_page": icon_samples,
            "source_video_url": f"https://www.youtube.com/watch?v={source_id}",
            "source_video_path": str(source.relative_to(ROOT)),
            "source_video_sha256": digest(source),
            "result_pdf_page": result_pages[0],
            "shot_pdf_pages": [row["pdf_page"] for row in ends],
            "official_end_count": len(ends),
            "official_shot_count": sum(row["shot_count"] for row in ends),
            "ends": ends,
        })
    result = {
        "status": "independent_official_shot_order_without_video_timestamps",
        "official_pdf_url": "https://curlit.com/PDF/PWG2022_ResultsBook.pdf",
        "official_pdf_path": str(PDF.relative_to(ROOT)),
        "official_pdf_sha256": digest(PDF),
        "parser_sha256": digest(ROOT / "prototype/official_shot_ledger.py"),
        "runner_sha256": digest(Path(__file__)),
        "games": games,
        "limitations": [
            "The official pages provide ordered deliveries, team, shooter and post-shot diagrams but no video timestamps.",
            "Stone positions in PDF diagrams are not extracted in this ledger.",
            "Video-to-official game identity uses published YouTube matchup titles, existing source selections, and matching session-one team pairings; individual shot-to-video alignment is not established.",
            "End scores and shot counts can bound errors, but cannot establish timestamped detector precision, recall or F1 by themselves.",
        ],
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    for game in games:
        print(game["official_game_code"], game["teams"], game["official_shot_count"],
              [row["shot_count"] for row in game["ends"]])


if __name__ == "__main__":
    main()
