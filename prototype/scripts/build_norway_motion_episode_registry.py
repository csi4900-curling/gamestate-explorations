"""Freeze an exact-track episode registry for the Norway motion transfer."""

from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from prototype.motion_episode_registry import build_registry


SOURCE = ROOT / "validation/official-shot-sequence/norway-full-event-motion-transfer-first.json"
REUSE = ROOT / "validation/official-shot-sequence/norway-motion-track-reuse-first.json"
OUTPUT = ROOT / "validation/official-shot-sequence/norway-motion-episode-registry-first.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first motion-episode registry")
    source = json.loads(SOURCE.read_text())
    reuse = json.loads(REUSE.read_text())
    source_hash = digest(SOURCE)
    if source_hash != reuse["motion_transfer_sha256"]:
        raise SystemExit("Source transfer has changed since the reuse audit")
    if len(source["rows"]) != source["candidate_count"]:
        raise SystemExit("Candidate rows and declared count disagree")
    registry = build_registry(source["rows"])
    if registry["episode_count"] != reuse["distinct_exact_track_count"]:
        raise SystemExit("Distinct exact-track count disagrees with reuse audit")
    if registry["shared_episode_count"] != reuse["reused_exact_track_count"]:
        raise SystemExit("Shared exact-track count disagrees with reuse audit")
    result = {
        "status": "source_only_exact_motion_episode_registry_not_physical_throw_assignment",
        "motion_transfer_sha256": source_hash,
        "reuse_audit_sha256": digest(REUSE),
        "registry_code_sha256": digest(ROOT / "prototype/motion_episode_registry.py"),
        "runner_sha256": digest(Path(__file__)),
        "candidate_count": len(source["rows"]),
        **registry,
        "limitations": [
            "An exact track is counted once even when several candidate windows contain it.",
            "Exclusive candidate linkage does not prove a distinct physical stone or throw; near-duplicate tracks may still be fragmented.",
            "Multiple episodes in a candidate window may include other moving stones or multiple camera observations.",
            "Shared episodes remain unresolved; no candidate is selected solely from motion.",
            "The candidate ledger and motion tracks are not independently labelled throw ground truth.",
        ],
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print({key: result[key] for key in
           ("candidate_count", "episode_count", "shared_episode_count", "candidate_motion_status_counts")})


if __name__ == "__main__":
    main()
