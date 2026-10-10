"""Source-colour concordance handoff across three exposed 2022 matches."""

from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cross_view_source_colour import join_source_colour

BASE = ROOT / "validation/official-shot-sequence"
PASSAGES = {
    "PREL000101": BASE / "swiss-provisional-release-transfer-first.json",
    "PREL000102": BASE / "china-provisional-release-transfer-first.json",
    "PREL000103": BASE / "slovakia-provisional-release-coverage-development.json",
}
POSTCUT = BASE / "pwg2022-visual-only-postcut-colours.json"
OUTPUT = BASE / "pwg2022-cross-view-source-colour-handoff-development.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def build():
    sidecar = json.loads(POSTCUT.read_text())
    by_game = {row["official_game_code_for_join_only"]: row for row in sidecar["games"]}
    if len(by_game) != len(sidecar["games"]):
        raise ValueError("Duplicate post-cut game")
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    games = []
    for code, path in PASSAGES.items():
        passage = json.loads(path.read_text())
        postcut = by_game[code]
        if (
            passage["source_sha256"] != postcut["source_video_sha256"]
            or passage["source_sha256"] == reserved["source_sha256"]
        ):
            raise ValueError(f"Source mismatch or reserved game: {code}")
        rows = join_source_colour(passage["rows"], postcut["rows"])
        games.append(
            {
                "recording_code": code,
                "source_sha256": passage["source_sha256"],
                "release_audit_sha256": digest(path),
                "unique_release_cue_count": len(rows),
                "source_colour_concordance_count": sum(
                    row["source_colour"] is not None for row in rows
                ),
                "source_colour_ledger_unknown_count": sum(
                    row["ledger_relation"] == "ledger_unknown" for row in rows
                ),
                "source_colour_ledger_conflict_count": sum(
                    row["ledger_relation"] == "conflicts_with_ledger" for row in rows
                ),
                "rows": rows,
            }
        )
    return {
        "status": "development_two_view_source_colour_handoff_not_identity_verified",
        "postcut_sha256": digest(POSTCUT),
        "join_code_sha256": digest(ROOT / "prototype/cross_view_source_colour.py"),
        "runner_sha256": digest(Path(__file__)),
        "games": games,
        "limitations": [
            "Both cues come from source video, but their agreement does not prove the same physical stone persists across a broadcast cut.",
            "The post-cut sidecar scans selected visual-only candidates, not every provisional event.",
            "Ledger conflicts are review/correction proposals; the existing ledger remains unchanged.",
            "All matches are exposed development sources; no independent physical event F1 or game-state accuracy is measured.",
        ],
    }


def main():
    payload = json.dumps(build(), indent=2) + "\n"
    if OUTPUT.exists():
        if OUTPUT.read_text() != payload:
            raise SystemExit("Existing source-colour handoff differs from inputs or code")
        print(f"Verified {OUTPUT}")
    else:
        OUTPUT.write_text(payload)
        print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
