"""Keep the game-state constraint tied to the official results-book page."""

import hashlib
import json
from pathlib import Path

import pymupdf

from prototype.scripts.audit_official_game_results import game_result


ROOT = Path(__file__).resolve().parents[2]
PDF = ROOT / "validation/official-shot-sequence/WWhCC2024_ResultsBook.pdf"
CONTEXT = ROOT / "validation/official-shot-sequence/latvia-canada-2024-end-score-context.json"


def test_latvia_canada_scores_match_results_book():
    context = json.loads(CONTEXT.read_text())
    assert hashlib.sha256(PDF.read_bytes()).hexdigest() == context["source"]["local_pdf_sha256"]
    pdf = pymupdf.open(PDF)
    result = game_result(pdf[context["source"]["pdf_page_index_zero_based"]].get_text(), "LAT")
    for row in context["teams"]:
        assert result["end_scores"][row["team"]][:6] == [str(n) for n in row["points_by_end"]]
        assert sum(row["points_by_end"]) == row["total_points"]
    assert result["completed_ends"] == list(range(1, context["completed_ends"] + 1))
    assert result["nominal_completed_end_deliveries"] == context["nominal_completed_end_deliveries"]
