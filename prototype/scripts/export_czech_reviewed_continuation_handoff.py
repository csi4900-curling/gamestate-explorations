"""Conserve all reviewed stone gaps while attaching causal cap evidence."""

from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from reviewed_stone_continuation_handoff import build_continuation_handoff  # noqa: E402

BASE = ROOT / "validation/throw-event-benchmark/canada-czech-2024"
GAPS = BASE / "full-reviewed-stone-replay-gaps-development.json"
CAPS = BASE / "full-reviewed-stone-cap-continuations-development.json"
LATER = BASE / "full-reviewed-later-board-onset-probes-development.json"
LATE = BASE / "e096-late-red-board-continuation-development.json"
LATE_SOURCE = BASE / "e096-late-red-source-probe/manifest.json"
OUT = BASE / "full-reviewed-stone-continuation-handoff-development.json"


def digest(path):
    h = sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def main():
    if OUT.exists():
        raise ValueError("Continuation handoff already exists")
    gaps, caps, later, late, source = (
        json.loads(p.read_text()) for p in (GAPS, CAPS, LATER, LATE, LATE_SOURCE)
    )
    if (
        caps["input_sha256"]["replay_gaps"] != digest(GAPS)
        or late["input_sha256"]["replay_gaps"] != digest(GAPS)
        or later["input_sha256"]["replay_gaps"] != digest(GAPS)
        or later["input_sha256"]["first_onset_cap_continuations"] != digest(CAPS)
        or caps["source_video_sha256"] != late["source_video_sha256"]
        or later["source_video_sha256"] != late["source_video_sha256"]
        or source["source_video_sha256"] != late["source_video_sha256"]
        or source["track_sha256"] != digest(LATE)
        or not source["frame_count"] == len(late["steps"])
    ):
        raise ValueError("Continuation input lineage differs")
    rows = build_continuation_handoff(gaps, caps, late, later)
    result = {
        "status": "reviewed_stone_continuation_handoff_not_simulation_ready",
        "source_video_sha256": caps["source_video_sha256"],
        "input_sha256": {
            "replay_gaps": digest(GAPS),
            "first_board_cap_continuations": digest(CAPS),
            "later_board_onset_probes": digest(LATER),
            "e096_late_board_continuation": digest(LATE),
            "e096_source_manifest": digest(LATE_SOURCE),
        },
        "builder_code_sha256": digest(ROOT / "prototype/reviewed_stone_continuation_handoff.py"),
        "runner_sha256": digest(Path(__file__)),
        "reviewed_stone_episode_count": len(rows),
        "board_blind_cap_continuation_count": sum(
            r["board_blind_cap_continuation"] is not None for r in rows
        ),
        "first_board_observation_horizon_reached_count": sum(
            bool(
                r["board_blind_cap_continuation"]
                and r["board_blind_cap_continuation"]["reached_first_board_observation_horizon"]
            )
            for r in rows
        ),
        "late_board_link_hypothesis_count": sum(
            r["late_board_link_hypothesis"] is not None for r in rows
        ),
        "later_board_onset_case_count": sum(
            bool(
                r["later_same_colour_board_onset_probe"]
                and r["later_same_colour_board_onset_probe"]["later_onset_checkpoints"]
            )
            for r in rows
        ),
        "rows": rows,
        "limitations": [
            "No cap path or colour match verifies a physical throw, persistent stone identity, complete board or simulation readiness.",
            "First same-colour partial-board observation can be an existing stone; E096's later V02 onset illustrates the failure of earliest-observation matching.",
            "All paths and local source review are post-inspection development evidence on one recording; event precision, recall and cross-recording transfer remain unmeasured.",
        ],
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                "episodes": len(rows),
                "cap_continuations": result["board_blind_cap_continuation_count"],
                "first_horizon_reached": result["first_board_observation_horizon_reached_count"],
                "late_links": result["late_board_link_hypothesis_count"],
            }
        )
    )


if __name__ == "__main__":
    main()
