"""Compare provisional 2024 timelines with the official game-results pages.

The 2024 wheelchair results book has end scores, not shot-by-shot records.
Completed ends give a nominal sixteen-delivery count, never event timestamps.
"""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

import pymupdf


MATCHES = {
    "Y_U6gzqORUs": ("CHN", 75),
    "PXGfMeiTKMA": ("EST", 69),
    "Vp3TIdOAlrc": ("ITA", 86),
}
VIDEO_TITLES = {
    "Y_U6gzqORUs": "CHN : CAN 중국 : 캐나다 - RR - WWhCC 2024",
    "PXGfMeiTKMA": "EST : CAN 에스토니아 : 캐나다 - RR - WWhCC 2024",
    "Vp3TIdOAlrc": "CAN : ITA 캐나다 : 이탈리아 - RR - WWhCC 2024",
}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def game_result(page_text, opponent):
    lines = page_text.splitlines()
    if "Game Results" not in lines or "CAN - Canada" not in lines:
        raise ValueError("Page is not a Canada game-results page")
    header = next(line for line in lines if line.startswith("Round Robin Session "))
    start_time = lines[0]
    date = lines[1]
    teams = {}
    for code in ("CAN", opponent):
        matches = [i for i, line in enumerate(lines) if line.startswith(f"{code} - ")]
        if not matches:
            raise ValueError(f"Missing team {code}")
        index = matches[0]
        values = lines[index + 1 : index + 9]
        if len(values) != 8 or any(not re.fullmatch(r"\d+|X", v) for v in values):
            raise ValueError(f"Invalid eight-end score row for {code}: {values}")
        teams[code] = values
    completed = [i + 1 for i in range(8) if all(teams[code][i] != "X" for code in teams)]
    if completed != list(range(1, len(completed) + 1)):
        raise ValueError("Completed ends are not a prefix")
    return {
        "date": date,
        "start_time": start_time,
        "session_sheet": header,
        "end_scores": teams,
        "completed_ends": completed,
        "nominal_completed_end_deliveries": 16 * len(completed),
        "end_eight_status": "reported_X_unplayed_or_unfinished"
        if any(teams[code][7] == "X" for code in teams)
        else "completed",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, required=True)
    parser.add_argument("--timelines-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists")
    pdf = pymupdf.open(args.pdf)
    rows = []
    for source_id, (opponent, page_number) in MATCHES.items():
        matches = list(args.timelines_dir.glob("*/timeline.json"))
        selected = [p for p in matches if json.loads(p.read_text())["source_id"] == source_id]
        if len(selected) != 1:
            raise ValueError(f"Expected exactly one timeline for {source_id}")
        timeline_path = selected[0]
        timeline = json.loads(timeline_path.read_text())
        result = game_result(pdf[page_number - 1].get_text(), opponent)
        colour_counts = dict(Counter(row["colour"] for row in timeline["observed_events"]))
        colour_excess = {
            colour: max(0, count - 8 * len(result["end_scores"]["CAN"]))
            for colour, count in colour_counts.items()
            if colour is not None
        }
        rows.append(
            {
                "source_id": source_id,
                "video_url": f"https://www.youtube.com/watch?v={source_id}",
                "published_video_title": VIDEO_TITLES[source_id],
                "opponent": opponent,
                "official_pdf_page": page_number,
                "timeline_path": str(timeline_path),
                "timeline_sha256": sha256(timeline_path),
                "provisional_event_count": timeline["observed_event_count"],
                "provisional_colour_counts": colour_counts,
                "colour_excess_over_eight_end_capacity": colour_excess,
                "provisional_minus_completed_end_nominal": (
                    timeline["observed_event_count"] - result["nominal_completed_end_deliveries"]
                ),
                "coverage_gaps_s": timeline["coverage_gaps_s"],
                **result,
            }
        )
    output = {
        "status": "development_count_audit_not_event_reference",
        "official_pdf_url": "https://curlit.com/PDF/WWhCC2024_ResultsBook.pdf?V=2",
        "official_pdf_sha256": sha256(args.pdf),
        "video_title_source": "YouTube oEmbed responses retrieved 2026-10-07",
        "limitations": [
            "Match identity is supported by YouTube's published title and official team pairing; the video scoreboard has not been independently checked.",
            "The results book contains end scores but no shot-by-shot pages for these games.",
            "Sixteen deliveries per completed end is a nominal rule count, not a video-timed event reference.",
            "Colour capacity assumes one handle colour per team and at most eight normally delivered stones per team per end.",
            "X marks unplayed or unfinished ends; their actual delivery count is unknown.",
            "A count discrepancy cannot identify a false or missed event, nor establish event precision or recall.",
        ],
        "games": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print(
        json.dumps(
            {row["opponent"]: row["provisional_minus_completed_end_nominal"] for row in rows}
        )
    )


if __name__ == "__main__":
    main()
