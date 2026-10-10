"""Join source-reviewed bridge crossings to conditional right-view links."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text())


def build_audit(classes_path, triage_path, manifest_path, patch_path, fusion_path):
    classes = load(classes_path)
    triage = load(triage_path)
    manifest = load(manifest_path)
    patch = load(patch_path)
    fusion = load(fusion_path)
    for field, path in [
        ("bridge_triage_sha256", triage_path),
        ("crossing_source_manifest_sha256", manifest_path),
        ("crossing_patch_diagnostic_sha256", patch_path),
    ]:
        if classes[field] != digest(path):
            raise ValueError(f"Stale source review: {field}")
    source_hash = classes["source_sha256"]
    if any(item["source_sha256"] != source_hash for item in (triage, manifest, patch, fusion)):
        raise ValueError("Source video fingerprints differ")
    if manifest["triage_sha256"] != digest(triage_path):
        raise ValueError("Source crops do not belong to this triage")

    candidates = {row["id"]: row for row in triage["new_review_candidates"]}
    review = {row["candidate_id"]: row for row in classes["rows"]}
    if len(candidates) != len(triage["new_review_candidates"]) or set(review) != set(candidates):
        raise ValueError("Source-review IDs must cover the distinct new bridge candidates")
    if len(review) != len(classes["rows"]):
        raise ValueError("Duplicate source-review ID")
    crop_ids = {event_id for sheet in manifest["sheets"] for event_id in sheet["event_ids"]}
    if crop_ids != set(candidates):
        raise ValueError("Crossing crops do not cover these bridge candidates")
    patch_ids = {
        row["event_id"] for row in patch["events"] if row["group"] == "bridged_review_candidate"
    }
    if patch_ids != set(candidates):
        raise ValueError("Crossing diagnostic candidate IDs differ")

    links = {}
    for entry in fusion["right_entries"]:
        left_id = entry["conditional_left_candidate_id"]
        if left_id in candidates:
            links.setdefault(left_id, []).append(entry)

    allowed_classes = {
        "stone_at_tracked_crossing",
        "nonstone_at_tracked_crossing",
        "occluded_identity_uncertain",
    }
    rows = []
    for candidate_id, candidate in candidates.items():
        source_class = review[candidate_id]["crossing_source_class"]
        if source_class not in allowed_classes:
            raise ValueError(f"Unknown source class: {source_class}")
        matched = links.get(candidate_id, [])
        if len(matched) > 1:
            raise ValueError(f"Multiple right links to {candidate_id}")
        entry = matched[0] if matched else None
        if entry and (
            entry["fusion_status"] != "cross_view_time_colour_corrob"
            or entry["right_colour_claim"] != candidate["colour_claim"]
            or entry["right_entry_time_s"] <= candidate["candidate_time_s"]
        ):
            raise ValueError(f"Inconsistent right link for {candidate_id}")
        rows.append(
            {
                "candidate_id": candidate_id,
                "crossing_time_s": candidate["candidate_time_s"],
                "crossing_source_class": source_class,
                "source_object": review[candidate_id].get("object"),
                "conditional_right_raw_track_id": entry["right_raw_track_id"] if entry else None,
                "right_minus_left_lag_s": entry["right_minus_left_lag_s"] if entry else None,
                "physical_throw_verified": False,
            }
        )
    counts = Counter(
        (row["crossing_source_class"], row["conditional_right_raw_track_id"] is not None)
        for row in rows
    )
    return {
        "status": "selected_development_crossing_audit_not_independent_event_validation",
        "source_sha256": source_hash,
        "source_classes_sha256": digest(classes_path),
        "bridge_triage_sha256": digest(triage_path),
        "crossing_source_manifest_sha256": digest(manifest_path),
        "crossing_patch_diagnostic_sha256": digest(patch_path),
        "bridged_fusion_sha256": digest(fusion_path),
        "runner_sha256": digest(Path(__file__)),
        "counts_by_source_class": {
            source_class: {
                "conditionally_linked": counts[source_class, True],
                "unlinked": counts[source_class, False],
            }
            for source_class in sorted(allowed_classes)
        },
        "rows": rows,
        "limitations": [
            "Selected bridge proposals were reviewed by the development agent, not independently or exhaustively labeled.",
            "A source-visible stone and a later same-colour right prefix do not prove one physical delivery or stone identity.",
            "The occluded case remains unresolved; conditional links must not be promoted to accepted throws automatically.",
            "These selected counts are not precision, recall, F1, or a measured filter operating point.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("classes", "triage", "manifest", "patch", "fusion", "output"):
        parser.add_argument(f"--{name}", required=True, type=Path)
    args = parser.parse_args()
    result = build_audit(args.classes, args.triage, args.manifest, args.patch, args.fusion)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result["counts_by_source_class"], sort_keys=True))


if __name__ == "__main__":
    main()
