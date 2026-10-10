"""Derive a contradiction-aware visual-only colour handoff from frozen inputs."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.candidate_cross_view_colour import reconcile_visual_only_colours  # noqa: E402

BASE = ROOT / "validation/throw-event-benchmark/paralympics-2022-korea-china"
LEDGER = (
    ROOT
    / "validation/curlobserver-learned-probe/korea-china-full-first-transfer/candidate-event-ledger.json"
)
POSTCUT = BASE / "VISUAL-ONLY-POSTCUT.json"
OUTPUT = BASE / "VISUAL-ONLY-COLOUR-HANDOFF.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    ledger = json.loads(LEDGER.read_text())
    postcut = json.loads(POSTCUT.read_text())
    if (
        postcut["first_transfer_ledger_sha256"] != digest(LEDGER)
        or postcut["source_video_sha256"] != ledger["source_sha256"]
    ):
        raise ValueError("Frozen ledger and post-cut audit differ")
    rows = reconcile_visual_only_colours(ledger["events"], postcut["rows"])
    result = {
        "status": "derived_visual_only_colour_evidence_not_physical_throw_identity",
        "source_video_sha256": ledger["source_sha256"],
        "candidate_ledger_sha256": digest(LEDGER),
        "postcut_audit_sha256": digest(POSTCUT),
        "reconciler_code_sha256": digest(ROOT / "prototype/candidate_cross_view_colour.py"),
        "runner_sha256": digest(Path(__file__)),
        "visual_only_candidate_count": len(rows),
        "relation_counts": dict(Counter(row["relation"] for row in rows)),
        "rows": rows,
        "limitations": [
            "Post-cut evidence was generated after the frozen first match transfer on exposed video.",
            "Two-view colour agreement does not prove one physical stone across the cut or confirm a throw.",
            "No row is game-state-ready; unscanned counter-linked candidates are outside this sidecar.",
        ],
    }
    payload = json.dumps(result, indent=2) + "\n"
    if OUTPUT.exists():
        if OUTPUT.read_text() != payload:
            raise SystemExit("Existing derived handoff differs from inputs or code")
        print(f"Verified {OUTPUT}")
    else:
        OUTPUT.write_text(payload)
        print(f"Wrote {OUTPUT}")
    print(result["relation_counts"])


if __name__ == "__main__":
    main()
