"""Freeze source-reviewed non-Latvia right patch training examples."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "validation/throw-event-benchmark"
SOURCES = (
    ("italy", "italy_r01", "canada-italy/source.mp4",
     "canada-italy/right-large-cap-full-r01-disagreements.json",
     "canada-italy/right-large-cap-full-r01-disagreement-source-review/source-prefix-classes.json"),
    ("estonia", "estonia_r01", "canada-estonia-2024/source.mp4",
     "canada-estonia-2024/right-large-cap-full-r01-disagreements.json",
     "canada-estonia-2024/right-large-cap-full-r01-disagreement-source-review/source-prefix-classes.json"),
    ("estonia", "estonia_r02", "canada-estonia-2024/source.mp4",
     "canada-estonia-2024/right-large-cap-full-r02-disagreements.json",
     "canada-estonia-2024/right-large-cap-full-r02-disagreement-source-review/source-prefix-classes.json"),
    ("usa", "usa_area", "canada-usa-2024/source.mp4",
     "canada-usa-2024/right-area-aware-postscore-development.json",
     "canada-usa-2024/right-area-aware-source-review/source-prefix-classes.json"),
    ("italy", "italy_global", "canada-italy/source.mp4",
     "canada-italy/right-global-area-fixed-transfer.json",
     "canada-italy/right-global-area-source-review/source-prefix-classes.json"),
    ("estonia", "estonia_global", "canada-estonia-2024/source.mp4",
     "canada-estonia-2024/right-global-area-postscore.json",
     "canada-estonia-2024/right-global-area-source-review/source-prefix-classes.json"),
)
OUT = BASE / "right-sideview-source-diverse-development-v1/selection.json"
CLASS = {"moving_stone": "stone_pixels",
         "person_or_wheelchair": "person_or_equipment_pixels",
         "person_or_wheelchair_or_equipment": "person_or_equipment_pixels"}


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def main():
    if OUT.exists():
        raise ValueError("Training selection already exists")
    sources, examples, excluded = [], [], []
    for match, inventory, video_rel, scan_rel, review_rel in SOURCES:
        video, scan_path, review_path = (BASE / path for path in (
            video_rel, scan_rel, review_rel))
        scan, review = json.loads(scan_path.read_text()), json.loads(
            review_path.read_text())
        video_hash = digest(video)
        if (scan["source_sha256"] != video_hash or
                review["source_sha256"] != video_hash or
                review["probe_sha256"] != digest(scan_path)):
            raise ValueError(f"{inventory} source lineage mismatch")
        proposals = {row["raw_track_id"]: row for row in scan[
            "directional_review_proposals"]}
        if (len(proposals) != len(scan["directional_review_proposals"]) or
                set(proposals) != {row["raw_track_id"] for row in review["rows"]}):
            raise ValueError(f"{inventory} review coverage mismatch")
        sources.append({"match": match, "inventory": inventory,
                        "video": video_rel, "video_sha256": video_hash,
                        "scan": scan_rel, "scan_sha256": digest(scan_path),
                        "review": review_rel, "review_sha256": digest(review_path)})
        for reviewed in review["rows"]:
            track = reviewed["raw_track_id"]
            source_class = reviewed["source_prefix_class"]
            if source_class not in CLASS:
                excluded.append({"inventory": inventory, "raw_track_id": track,
                                 "source_prefix_class": source_class})
                continue
            points = {point["time_s"]: point for point in proposals[track][
                "observed_prefix_points"]}
            times = reviewed["sample_source_times_s"]
            if len(times) != 3 or not all(t in points for t in times):
                raise ValueError(f"{inventory}:{track} samples differ")
            examples.append({
                "example_id": f"{inventory}:{track}",
                "match": match,
                "inventory": inventory,
                "raw_track_id": track,
                "source_prefix_class": source_class,
                "training_pixel_class": CLASS[source_class],
                "samples": [{"time_s": t, "cap_bbox_px": points[t]["bbox"]}
                            for t in times],
            })
    if len({e["example_id"] for e in examples}) != len(examples):
        raise ValueError("Duplicate training example identity")
    counts = Counter((e["match"], e["training_pixel_class"]) for e in examples)
    result = {
        "status": "non_latvia_development_patch_training_selection_not_event_truth",
        "sources": sources,
        "selection_rule": "All reviewed moving_stone and person/wheelchair/equipment three-frame prefixes in six preexisting 2024 right inventories; exclude uncertain, mixed and person-handled stones; no Latvia examples",
        "example_count": len(examples),
        "excluded_count": len(excluded),
        "counts_by_match_class": {match: {cls: counts[match, cls] for cls in (
            "stone_pixels", "person_or_equipment_pixels")}
            for match in ("italy", "estonia", "usa")},
        "examples": examples,
        "excluded": excluded,
        "runner_sha256": digest(Path(__file__)),
        "limitations": [
            "Labels are selected same-agent short-prefix source-pixel reviews, not independent physical throw truth.",
            "Some examples from the same match or physical path occur in more than one inventory; exact duplicate crops must be deduplicated during fitting.",
            "Source matches share broadcast conventions, so leave-one-match-out checks still cannot prove production generalization.",
            "Latvia labels and source frames are excluded from fitting but were already inspected during model-design work; its later score is development transfer, not a sealed holdout.",
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"examples": len(examples), "excluded": len(excluded),
                      "counts": result["counts_by_match_class"]}))


if __name__ == "__main__":
    main()
