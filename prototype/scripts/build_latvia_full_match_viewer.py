"""Build a file-openable data bundle for the Latvia evidence explorer."""

from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INPUT = (
    ROOT
    / "validation/throw-event-benchmark/layout-router/full-2024-coverage/latvia24-full-v1/full-match-candidate-partial-state-handoff.json"
)
OUTPUT_DIR = ROOT / "validation/throw-event-benchmark/canada-latvia-2024/full-match-review"
VIDEO = OUTPUT_DIR.parent / "source-360p.mp4"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    data_path = OUTPUT_DIR / "data.js"
    provenance_path = OUTPUT_DIR / "provenance.json"
    if data_path.exists() or provenance_path.exists():
        raise SystemExit("Viewer data or provenance already exists")
    handoff = json.loads(INPUT.read_text())
    if digest(VIDEO) != handoff["source_sha256"]:
        raise ValueError("Viewer video differs from candidate handoff source")
    if handoff["candidate_count"] != len(handoff["ordered_candidates"]):
        raise ValueError("Candidate count differs")
    rows = []
    for row in handoff["ordered_candidates"]:
        if row["physical_throw_verified"] or row["game_state_after"]["simulation_ready"]:
            raise ValueError("Unexpected physical or simulation-ready row")
        rows.append(
            {
                key: row[key]
                for key in (
                    "sequence_id",
                    "candidate_id",
                    "source_time_s",
                    "time_semantics",
                    "colour_claim",
                    "observation_kind",
                    "evidence_tier",
                    "left_screen_reason",
                    "left_coverage_status",
                    "observed_motion",
                    "post_candidate_partial_board",
                    "source_pixel_review",
                    "physical_throw_verified",
                    "game_state_after",
                )
            }
        )
    data = {
        "source_id": handoff["source_id"],
        "source_duration_s": handoff["source_interval_s"][1],
        "routed_coverage_gaps_s": handoff["routed_coverage_gaps_s"],
        "left_trigger_blind_intervals": handoff["left_trigger_blind_intervals"],
        "candidate_counts_by_kind": handoff["candidate_counts_by_kind"],
        "ordered_candidates": rows,
        "right_adjacent_partial_cap_transitions": handoff["right_adjacent_partial_cap_transitions"],
        "complete_throw_sequence_verified": False,
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    data_path.write_text(
        "window.CURLING_DATA = "
        + json.dumps(data, separators=(",", ":"), ensure_ascii=False)
        + ";\n"
    )
    provenance = {
        "status": "prediction_visible_evidence_viewer_not_independent_labels",
        "handoff_sha256": digest(INPUT),
        "source_video_sha256": digest(VIDEO),
        "runner_sha256": digest(Path(__file__)),
        "data_sha256": digest(data_path),
        "ui_sha256": {
            name: digest(OUTPUT_DIR / name) for name in ("index.html", "style.css", "app.js")
        },
        "candidate_count": len(rows),
        "limitations": [
            "The viewer exposes model predictions and must not be used for blind validation.",
            "Image-space cap positions and motion prefixes do not establish physical stone identity or complete game state.",
        ],
    }
    provenance_path.write_text(json.dumps(provenance, indent=2) + "\n")
    print(json.dumps({"rows": len(rows), "data_bytes": data_path.stat().st_size}))


if __name__ == "__main__":
    main()
