"""Screen existing counter-order review proposals with source-only colour."""

from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from counter_order_colour_screen import screen_order_proposals

ORDER = ROOT / "validation/official-shot-sequence/pwg2022-counter-sequence-order-development.json"
POSTCUT = ROOT / "validation/official-shot-sequence/pwg2022-visual-only-postcut-colours.json"
OUTPUT = (
    ROOT / "validation/official-shot-sequence/pwg2022-counter-order-colour-screen-development.json"
)


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def build():
    order = json.loads(ORDER.read_text())
    postcut = json.loads(POSTCUT.read_text())
    sidecars = {row["official_game_code_for_join_only"]: row for row in postcut["games"]}
    if len(sidecars) != len(postcut["games"]):
        raise ValueError("Duplicate post-cut game")
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    games = []
    for game in order["games"]:
        source = game["source_sha256"]
        if source == reserved["source_sha256"]:
            raise ValueError("Reserved source in colour screen")
        sidecar = sidecars.get(game["recording_code"])
        if sidecar is not None and sidecar["source_video_sha256"] != source:
            raise ValueError("Colour sidecar source mismatch")
        screened = screen_order_proposals(
            game["multi_option_counter_proposals"], sidecar["rows"] if sidecar else []
        )
        games.append(
            {
                "recording_code": game["recording_code"],
                "source_sha256": source,
                "sidecar_available": sidecar is not None,
                "screened_unique_order_proposal_count": len(screened),
                "visual_colour_conflict_count": sum(
                    row["screen_status"] == "visual_colour_conflict" for row in screened
                ),
                "visual_colour_abstention_count": sum(
                    row["screen_status"] == "visual_colour_abstained" for row in screened
                ),
                "rows": screened,
            }
        )
    return {
        "status": "development_source_colour_screen_no_counter_or_event_mutation",
        "input_sha256": {"order_audit": digest(ORDER), "visual_only_postcut": digest(POSTCUT)},
        "code_sha256": digest(ROOT / "prototype/counter_order_colour_screen.py"),
        "runner_sha256": digest(Path(__file__)),
        "games": games,
        "limitations": [
            "The post-cut sidecar covers visual-only candidates in three exposed 2022 recordings, not Norway.",
            "A post-cut moving stone need not be the delivered stone from the preceding view.",
            "Unknown or conflicting colour blocks automatic linking; matching colour still does not prove identity.",
            "This is a source-only development screen, not independent event precision or recall.",
        ],
    }


def main():
    payload = json.dumps(build(), indent=2) + "\n"
    if OUTPUT.exists():
        if OUTPUT.read_text() != payload:
            raise SystemExit("Existing colour screen differs from inputs or code")
        print(f"Verified {OUTPUT}")
    else:
        OUTPUT.write_text(payload)
        print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
