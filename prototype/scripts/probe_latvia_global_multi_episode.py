"""Apply quiet-separated multi-episode proposal extraction to saved global tracks."""

from hashlib import sha256
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from right_multi_episode_span import multi_episode_spans  # noqa: E402

BASE = ROOT / "validation/throw-event-benchmark/canada-latvia-2024"
SCAN = BASE / "full-right-global-area-development.json"
VIDEO = BASE / "source-360p.mp4"
OUT = BASE / "full-right-global-multi-episode-development.json"


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def main():
    if OUT.exists():
        raise ValueError("Multi-episode diagnostic already exists")
    scan = json.loads(SCAN.read_text())
    if scan["source_sha256"] != digest(VIDEO):
        raise ValueError("Global scan and source video differ")
    proposals = multi_episode_spans(scan["raw_tracks"])
    first = {row["raw_track_id"]: row for row in proposals if row[
        "episode_index_within_raw_track"] == 1}
    baseline = {row["raw_track_id"]: row for row in scan[
        "directional_review_proposals"]}
    if len(first) != len(baseline) or set(first) != set(baseline):
        raise ValueError("Multi-episode extraction lost baseline proposals")
    for track_id, row in first.items():
        clean = {key: value for key, value in row.items() if key not in (
            "episode_index_within_raw_track", "preceding_quiet_end_time_s",
            "raw_track_not_physical_identity")}
        if clean != baseline[track_id]:
            raise ValueError(f"First proposal changed: {track_id}")
    later = [row for row in proposals if row["episode_index_within_raw_track"] > 1]
    if len(proposals) != 118 or len(later) != 4:
        raise ValueError("Later-episode inventory differs")
    result = {
        "status": "postinspection_global_raw_track_multi_episode_development_not_throw_truth",
        "source_sha256": digest(VIDEO),
        "global_scan_sha256": digest(SCAN),
        "multi_episode_code_sha256": digest(
            ROOT / "prototype/right_multi_episode_span.py"),
        "late_seed_code_sha256": digest(ROOT / "prototype/right_late_seed_span.py"),
        "runner_sha256": digest(Path(__file__)),
        "source_interval_s": scan["source_interval_s"],
        "raw_track_count": scan["raw_track_count"],
        "baseline_first_episode_proposal_count": len(first),
        "later_quiet_separated_proposal_count": len(later),
        "all_review_proposal_count": len(proposals),
        "quiet_steps": 3,
        "quiet_rate_px_s": 3,
        "max_sample_gap_s": 1.5,
        "later_review_proposals": later,
        "limitations": [
            "The method was added after inspecting the global A452 miss on Latvia.",
            "A colour track can switch physical objects; later spans are image-motion proposals, not same-stone continuations.",
            "Quiet and displacement rules can still admit people, wheelchairs and equipment.",
            "This inventory has no independent physical throw count or event accuracy score.",
        ],
    }
    OUT.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"first_episodes": len(first), "later_episodes": len(later),
                      "all_review_proposals": len(proposals)}))


if __name__ == "__main__":
    main()
