"""Compare cut-aware Norway tracks with the frozen baseline without forcing throws."""

from hashlib import sha256
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from prototype.motion_episode_near_duplicates import find_near_duplicate_pairs
from prototype.motion_episode_registry import build_registry


BASELINE = ROOT / "validation/official-shot-sequence/norway-full-event-motion-transfer-first.json"
CUT_AWARE = ROOT / "validation/official-shot-sequence/norway-full-event-motion-cut-aware-v2.json"
OUTPUT = ROOT / "validation/official-shot-sequence/norway-cut-aware-episode-links-v2.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve cut-aware episode-link audit")
    baseline = json.loads(BASELINE.read_text())
    cut_aware = json.loads(CUT_AWARE.read_text())
    if cut_aware["baseline_motion_transfer_sha256"] != digest(BASELINE):
        raise SystemExit("Cut-aware transfer did not use this baseline")
    old_ids = [row["shot_id"] for row in baseline["rows"]]
    new_ids = [row["shot_id"] for row in cut_aware["rows"]]
    if old_ids != new_ids or len(new_ids) != 141:
        raise SystemExit("Candidate order or count changed")
    registry = build_registry(cut_aware["rows"])
    near_pairs = find_near_duplicate_pairs(registry["episodes"])
    losses = [new["shot_id"] for old, new in zip(baseline["rows"], cut_aware["rows"])
              if old["any_supported_motion"] and not new["any_supported_motion"]]
    gains = [new["shot_id"] for old, new in zip(baseline["rows"], cut_aware["rows"])
             if not old["any_supported_motion"] and new["any_supported_motion"]]
    result = {
        "status": "source_only_cut_aware_episode_link_audit_not_physical_throw_assignment",
        "baseline_motion_transfer_sha256": digest(BASELINE),
        "cut_aware_motion_transfer_sha256": digest(CUT_AWARE),
        "registry_code_sha256": digest(ROOT / "prototype/motion_episode_registry.py"),
        "near_duplicate_code_sha256": digest(ROOT / "prototype/motion_episode_near_duplicates.py"),
        "runner_sha256": digest(Path(__file__)),
        "candidate_count": len(new_ids),
        "baseline_supported_candidates": sum(row["any_supported_motion"] for row in baseline["rows"]),
        "cut_aware_supported_candidates": sum(row["any_supported_motion"] for row in cut_aware["rows"]),
        "support_lost_after_cut_breaks": losses,
        "support_gained_after_cut_breaks": gains,
        "cut_aware_episode_count": registry["episode_count"],
        "cut_aware_shared_episode_count": registry["shared_episode_count"],
        "candidate_motion_status_counts": registry["candidate_motion_status_counts"],
        "possible_near_duplicate_pairs": near_pairs,
        "episodes": registry["episodes"],
        "candidates": registry["candidates"],
        "limitations": [
            "Hard-cut detection catches only obvious frame changes at the 1 Hz sample rate.",
            "Exact and near-duplicate links are candidate-window diagnostics, not verified physical stone identity.",
            "Lost motion support does not reject a throw; within-shot evidence may remain outside this narrow cap rule.",
            "No independent physical throw F1 is inferred.",
        ],
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print({key: result[key] for key in
           ("baseline_supported_candidates", "cut_aware_supported_candidates",
            "support_lost_after_cut_breaks", "cut_aware_episode_count",
            "cut_aware_shared_episode_count", "candidate_motion_status_counts")})
    print("near_pairs", [row["episode_ids"] for row in near_pairs])


if __name__ == "__main__":
    main()
