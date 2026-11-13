"""Select source-reviewed crossing pixels for a frozen appearance probe."""

from hashlib import sha256
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LATVIA_AUDIT = (
    ROOT
    / "validation/throw-event-benchmark/canada-latvia-2024/crossing-shape-source-audit-development.json"
)
ITALY_AUDIT = (
    ROOT / "validation/throw-event-benchmark/canada-italy/shape-veto-s03-source-audit/manifest.json"
)
LATVIA_TIMELINE = (
    ROOT
    / "validation/throw-event-benchmark/layout-router/full-2024-coverage/latvia24-full-v1/timeline.json"
)
ITALY_TIMELINE = (
    ROOT
    / "validation/throw-event-benchmark/layout-router/full-2024-coverage/new-preflight-italy24/timeline.json"
)
LATVIA_RAW = (
    ROOT
    / "validation/throw-event-benchmark/layout-router/full-2024-coverage/latvia24-full-v1/run-02/events.json"
)
OUT = (
    ROOT
    / "validation/official-shot-sequence/latvia-italy-crossing-patch-source-class-selection.json"
)


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    latvia = json.loads(LATVIA_AUDIT.read_text())
    italy = json.loads(ITALY_AUDIT.read_text())
    latvia_timeline = json.loads(LATVIA_TIMELINE.read_text())
    italy_timeline = json.loads(ITALY_TIMELINE.read_text())
    latvia_raw = json.loads(LATVIA_RAW.read_text())
    if (
        latvia_timeline["source_sha256"] != latvia_raw["source_sha256"]
        or digest(LATVIA_RAW) != latvia["input_sha256"]["raw_left"]
    ):
        raise ValueError("Latvia source lineage mismatch")
    if italy_timeline["source_sha256"] != italy["source_video_sha256"]:
        raise ValueError("Italy source lineage mismatch")

    accepted_ids = {row["id"] for row in latvia_timeline["observed_events"]}
    selected = [
        {
            "id": f"R01-{row['candidate_id']}",
            "review": row["source_category"],
            "review_kind": "same_agent_postproposal_source_pixel_review",
        }
        for row in latvia["rows"]
        if row["raw_decision"] == "accepted"
        and row["source_category"] in ("stone_shaped_pixels", "person_pixels")
        and f"R01-{row['candidate_id']}" in accepted_ids
    ]
    if len(selected) != 13:
        raise ValueError(
            f"Expected 12 stone-pixel and one person-pixel Latvia rows, got {len(selected)}"
        )
    result = {
        "status": "postreview_frozen_model_source_pixel_probe_selection_not_event_truth",
        "input_sha256": {
            "latvia_review_audit": digest(LATVIA_AUDIT),
            "italy_source_audit": digest(ITALY_AUDIT),
            "latvia_timeline": digest(LATVIA_TIMELINE),
            "italy_timeline": digest(ITALY_TIMELINE),
        },
        "limitations": [
            "Source-pixel classes were assigned by the development agent after candidate proposals.",
            "A stone-shaped crossing pixel is not a verified physical throw.",
            "Only reviewed accepted Latvia candidates and one selected Italy stone path are included.",
        ],
        "sources": [
            {
                "source_id": latvia_timeline["source_id"],
                "video": "validation/throw-event-benchmark/canada-latvia-2024/source-360p.mp4",
                "timeline": str(LATVIA_TIMELINE.relative_to(ROOT)),
                "events": selected,
            },
            {
                "source_id": italy_timeline["source_id"],
                "video": "validation/source-cache/Vp3TIdOAlrc-360p.mp4",
                "timeline": str(ITALY_TIMELINE.relative_to(ROOT)),
                "events": [
                    {
                        "id": "R01-S03",
                        "review": "stone_shaped_pixels",
                        "review_kind": "same_agent_postproposal_source_pixel_review",
                    }
                ],
            },
        ],
    }
    OUT.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(f"Selected {len(selected)} Latvia and one Italy crossing")


if __name__ == "__main__":
    main()
