"""Flag Czech raw paths with later right-view patch and path agreement."""

from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark"
RUN = BASE / "layout-router/czech24-full-camera-motion-v1"
RAW = RUN / "run-02/raw.json"
EVENTS = RUN / "run-02/events.json"
OLD_RAW = BASE / "canada-czech-2024/full-match-stage1-raw-postscore.json"
HANDOFF = BASE / "canada-czech-2024/full-source-diverse-episode-state-handoff-development.json"
RIGHT_PATCH = BASE / "canada-czech-2024/full-right-source-diverse-patch-transfer-development.json"
OUT = RUN / "dual-observer-corroboration-development.json"

MAX_LAG_S = 20.0
MIN_POSITIVE_PATCHES = 2
MIN_SHARED_SAMPLES = 2
MAX_MEDIAN_CENTRE_DISTANCE_PX_360 = 3.0


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def main():
    if OUT.exists():
        raise ValueError("Dual-observer audit already exists")
    raw, events, old_raw, handoff, patches = (
        json.loads(path.read_text()) for path in (RAW, EVENTS, OLD_RAW, HANDOFF, RIGHT_PATCH)
    )
    source = raw["source_sha256"]
    if any(
        value != source
        for value in (
            events["source_sha256"],
            old_raw["source_sha256"],
            handoff["source_video_sha256"],
            patches["source_video_sha256"],
        )
    ):
        raise ValueError("Source mismatch")
    if handoff["input_sha256"]["patch_scores"] != digest(RIGHT_PATCH):
        raise ValueError("Handoff references different right-patch evidence")
    signature = lambda artifact: [
        (row["id"], row["crossing_time_s"], row["colour"]) for row in artifact["events"]
    ]
    if signature(raw) != signature(old_raw):
        raise ValueError("Old and current raw proposals differ")
    right_by_id = {row["right_proposal_id"]: row for row in patches["rows"]}
    if len(right_by_id) != len(patches["rows"]):
        raise ValueError("Repeated right proposal IDs")
    by_id = {}
    for episode in handoff["episodes"]:
        for member in episode.get("left_members", []):
            id = member["full_match_candidate_id"]
            if id in by_id:
                raise ValueError(f"Repeated left candidate ID: {id}")
            by_id[id] = episode
    confirmed = {row["id"] for row in events["events"]}
    rows = []
    for candidate in raw["events"]:
        id, time_s = candidate["id"], candidate["crossing_time_s"]
        episode = by_id.get(id)
        supports = []
        if episode:
            for pair in episode["cross_resolution_candidate_pair_evidence"]:
                if pair["left_candidate_id"] != id:
                    continue
                right = right_by_id[pair["right_proposal_id"]]
                lag = right["passage_time_s"] - time_s
                distance = pair["median_center_distance_px_360"]
                if (
                    0 <= lag <= MAX_LAG_S
                    and right["positive_patch_count"] >= MIN_POSITIVE_PATCHES
                    and pair["sampled_time_overlap_count"] >= MIN_SHARED_SAMPLES
                    and distance is not None
                    and distance <= MAX_MEDIAN_CENTRE_DISTANCE_PX_360
                ):
                    supports.append(
                        {
                            "right_proposal_id": right["right_proposal_id"],
                            "right_passage_time_s": right["passage_time_s"],
                            "lag_from_left_passage_s": lag,
                            "positive_patch_count": right["positive_patch_count"],
                            "sampled_time_overlap_count": pair["sampled_time_overlap_count"],
                            "median_center_distance_px_360": distance,
                        }
                    )
        rows.append(
            {
                "candidate_id": id,
                "passage_time_s": time_s,
                "context_confirmed": id in confirmed,
                "dual_observer_supported": bool(supports),
                "supporting_right_proposals": supports,
            }
        )
    supported = [row for row in rows if row["dual_observer_supported"]]
    recovered = [row["candidate_id"] for row in supported if not row["context_confirmed"]]
    OUT.write_text(
        json.dumps(
            {
                "status": "development_dual_observer_support_not_physical_throw_classification",
                "source_sha256": source,
                "input_sha256": {
                    "current_raw": digest(RAW),
                    "current_events": digest(EVENTS),
                    "old_raw": digest(OLD_RAW),
                    "old_handoff": digest(HANDOFF),
                    "old_right_patch": digest(RIGHT_PATCH),
                },
                "runner_sha256": digest(Path(__file__)),
                "criteria": {
                    "right_lag_s": [0, MAX_LAG_S],
                    "minimum_positive_right_patches": MIN_POSITIVE_PATCHES,
                    "minimum_cross_resolution_shared_samples": MIN_SHARED_SAMPLES,
                    "maximum_median_center_distance_px_360": MAX_MEDIAN_CENTRE_DISTANCE_PX_360,
                },
                "raw_candidate_count": len(rows),
                "dual_observer_supported_count": len(supported),
                "context_withheld_but_dual_observer_supported_ids": recovered,
                "rows": rows,
                "limitations": [
                    "The criteria are an exposed Czech development hypothesis, not a validated precision or recall rule.",
                    "Both observer paths can use the same source pixels; agreement does not establish physical stone identity.",
                    "The historical high-resolution handoff is expensive and has not been routed automatically for every source layout.",
                    "A candidate without support may still be a physical throw; absence is not a veto.",
                ],
            },
            indent=2,
        )
        + "\n"
    )
    print(json.dumps({"supported": len(supported), "context_withheld_supported": recovered}))


if __name__ == "__main__":
    main()
