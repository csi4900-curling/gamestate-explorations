"""Combine visual-only appearance and release cues without discarding proposals."""

from collections import Counter


def join_evidence(patch_rows, release_rows):
    patch = {row["candidate_id"]: row for row in patch_rows}
    release = {row["candidate_id"]: row for row in release_rows}
    if (
        len(patch) != len(patch_rows)
        or len(release) != len(release_rows)
        or set(patch) != set(release)
    ):
        raise ValueError("Patch and release candidate IDs differ or repeat")
    rows = []
    for candidate_id in patch:
        a, b = patch[candidate_id], release[candidate_id]
        if a["release_window_s"] != b["release_window_s"] or (
            a["candidate_colour"] != b["candidate_colour"]
        ):
            raise ValueError(f"Candidate evidence mismatch: {candidate_id}")
        appearance = a["patch_evidence_status"] == "stone_like_patch_track_present"
        passage = b["status"] == "unique_colour_compatible_passage"
        pattern = (
            "both_cues"
            if appearance and passage
            else "appearance_only"
            if appearance
            else "release_only"
            if passage
            else "neither_cue"
        )
        rows.append(
            {
                "candidate_id": candidate_id,
                "release_window_s": a["release_window_s"],
                "candidate_colour": a["candidate_colour"],
                "appearance_status": a["patch_evidence_status"],
                "release_status": b["status"],
                "evidence_pattern": pattern,
                "retained_for_event_review": True,
                "physical_throw_verified": False,
            }
        )
    return {
        "candidate_count": len(rows),
        "evidence_pattern_counts": dict(Counter(row["evidence_pattern"] for row in rows)),
        "rows": rows,
        "limitations": [
            "The two cues share underlying cap pixels and are not statistically independent.",
            "Neither cue proves a distinct throw; absence of either cannot veto off-camera events.",
            "All visual-only proposals are retained, including those with neither cue.",
        ],
    }
