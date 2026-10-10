"""Select every accepted Latvia left crossing for frozen patch scoring."""

from hashlib import sha256
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TIMELINE = ROOT / "validation/throw-event-benchmark/layout-router/full-2024-coverage/latvia24-full-v1/timeline.json"
AUDIT = ROOT / "validation/throw-event-benchmark/canada-latvia-2024/crossing-shape-source-audit-development.json"
VIDEO = ROOT / "validation/throw-event-benchmark/canada-latvia-2024/source-360p.mp4"
OUT = ROOT / "validation/throw-event-benchmark/canada-latvia-2024/all-accepted-left-crossing-patch-selection.json"


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def main():
    timeline = json.loads(TIMELINE.read_text())
    audit = json.loads(AUDIT.read_text())
    if digest(VIDEO) != timeline["source_sha256"]:
        raise ValueError("Latvia video differs from accepted event timeline")
    reviewed = {"R01-" + row["candidate_id"]: row["source_category"]
                for row in audit["rows"] if row["raw_decision"] == "accepted"}
    ids = {row["id"] for row in timeline["observed_events"]}
    if len(ids) != 72 or not set(reviewed) <= ids:
        raise ValueError("Accepted crossing inventory or reviewed IDs differ")
    selected = [{
        "id": event["id"],
        "review": reviewed.get(event["id"], "unreviewed"),
        "review_kind": ("same_agent_postproposal_source_pixel_review"
                        if event["id"] in reviewed else "unreviewed_full_prediction_catalog"),
    } for event in timeline["observed_events"]]
    result = {
        "status": "all_accepted_left_crossing_patch_selection_not_throw_truth",
        "input_sha256": {"timeline": digest(TIMELINE), "source_pixel_audit": digest(AUDIT)},
        "limitations": [
            "The 72 events are detector-accepted passages, not independently verified throws.",
            "The source classes are same-agent postproposal reviews; unreviewed is an explicit unknown.",
            "Crossing-local appearance scores are triage evidence and cannot safely reject a passage.",
        ],
        "sources": [{
            "source_id": timeline["source_id"],
            "video": str(VIDEO.relative_to(ROOT)),
            "timeline": str(TIMELINE.relative_to(ROOT)),
            "events": selected,
        }],
    }
    OUT.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(f"Selected {len(selected)} accepted Latvia left crossings")


if __name__ == "__main__":
    main()
