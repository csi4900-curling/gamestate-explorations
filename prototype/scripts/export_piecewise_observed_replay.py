"""Export all end-three cross-view observations as honest replay segments."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from observed_replay_handoff import build_observed_replay


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "cross-view",
        "source-meta",
        "provenance",
        "video",
        "segments-dir",
        "departure-dir",
        "output",
    ):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists")
    cross_view, source_meta, provenance = (
        json.loads(path.read_text())
        for path in (args.cross_view, args.source_meta, args.provenance)
    )
    video_hash = digest(args.video)
    if video_hash != source_meta["display_video"]["sha256"]:
        raise ValueError("Source video fingerprint differs")
    source_rows = cross_view["throws"]
    if len(source_rows) != cross_view["summary"]["throws"] or len(
        {row["id"] for row in source_rows}
    ) != len(source_rows):
        raise ValueError("Cross-view throw inventory differs")
    if [row["gate_time_s"] for row in source_rows] != sorted(
        row["gate_time_s"] for row in source_rows
    ):
        raise ValueError("Throw candidates are out of time order")
    rows = []
    segment_hashes = {}
    departure_hashes = {}
    for throw in source_rows:
        departure_relative = f"cross-view/{throw['id']}-departure.json"
        departure_path = args.departure_dir / f"{throw['id']}-departure.json"
        departure_hash = digest(departure_path)
        if provenance["observation_sha256"].get(departure_relative) != departure_hash:
            raise ValueError(f"Departure lineage differs: {throw['id']}")
        departure_source = json.loads(departure_path.read_text())
        if departure_source["event_id"] != throw["id"]:
            raise ValueError(f"Departure identity differs: {throw['id']}")
        source_records = iter(departure_source["records"])
        for selected in throw["departure"]:
            if not any(
                all(
                    record.get(key) == selected.get(key)
                    for key in ("time_s", "pixel", "position_local_m")
                )
                for record in source_records
            ):
                raise ValueError(f"Departure observation differs: {throw['id']}")
        relative = f"throw-segments/{throw['id']}.json"
        path = args.segments_dir / f"{throw['id']}.json"
        file_hash = digest(path)
        if provenance["observation_sha256"].get(relative) != file_hash:
            raise ValueError(f"Segment lineage differs: {throw['id']}")
        segment = json.loads(path.read_text())
        if segment["event"]["id"] != throw["id"] or segment["event"]["colour"] != throw["colour"]:
            raise ValueError("Segment event identity differs")
        row = build_observed_replay(throw, segment)
        source_gap = throw["gap"]["duration_s"]
        if throw["id"] == "T11" and throw.get("display_arrival"):
            handoff = throw["expanded_handoff"]
            if (
                row["seam"]["status"] != "same_time_projections_disagree_unresolved"
                or abs(
                    row["seam"]["same_time_longitudinal_difference_m"]
                    - handoff["longitudinal_disagreement_m"]
                )
                > 0.001
                or abs(
                    row["seam"]["same_time_lateral_difference_m"]
                    - handoff["lateral_disagreement_m"]
                )
                > 0.001
            ):
                raise ValueError("T11 expanded handoff mismatch")
            row["source_processing_note"] = (
                "Range-expanded receiving points replace the initial bounded "
                "gap for piecewise replay; far geometry is unvalidated."
            )
            row["initial_bounded_processing_gap_s"] = round(source_gap, 6)
        else:
            if abs(row["seam"]["sampled_time_gap_s"] - source_gap) > 0.001:
                raise ValueError("Original camera gap differs")
            row["source_processing_note"] = (
                "The sampled gap is unobserved by the accepted processing, "
                "not proof that the stone is invisible in source video."
            )
            row["initial_bounded_processing_gap_s"] = round(source_gap, 6)
        rows.append(row)
        segment_hashes[throw["id"]] = file_hash
        departure_hashes[throw["id"]] = departure_hash
    output = {
        "status": "piecewise_source_observation_replay_not_physical_simulation",
        "source_video_sha256": video_hash,
        "source_interval_s": source_meta["source_interval_s"],
        "input_sha256": {
            "cross_view": digest(args.cross_view),
            "source_meta": digest(args.source_meta),
            "provenance": digest(args.provenance),
            "departures_by_id": departure_hashes,
            "segments_by_id": segment_hashes,
        },
        "model_code_sha256": digest(ROOT / "prototype/observed_replay_handoff.py"),
        "runner_sha256": digest(Path(__file__)),
        "coordinate_frame": {
            "unit": "metres_conditional",
            "origin": "departure_tee",
            "axes": cross_view["configuration"]["global_axes"],
            "nominal_tee_distance_m": cross_view["configuration"]["tee_distance_m"],
            "orientation_status": cross_view["configuration"]["orientation_status"],
            "metric_accuracy_validated": False,
        },
        "candidate_count": len(rows),
        "piecewise_observation_replay_count": sum(
            row["piecewise_observation_replay_available"] for row in rows
        ),
        "physics_simulation_ready_count": sum(row["physics_simulation_ready"] for row in rows),
        "visually_stable_delivered_stone_candidate_count": sum(
            row["visually_stable_delivered_stone_candidate"] is not None for row in rows
        ),
        "interpolated_cross_camera_points": 0,
        "events": rows,
        "limitations": [
            "Cross-view identity and orientation were developed on this end and lack independent validation.",
            "World positions use nominal rink geometry and conditional cap-height correction.",
            "No trajectory is interpolated across a gap or fused across a disagreeing same-time seam.",
            "Visual stability of a candidate delivered stone does not establish physical settling or a complete board.",
            "Physical release, spin, stone identity, collisions, full game state and physics parameters remain unknown.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print(
        json.dumps(
            {
                "candidates": len(rows),
                "replay": output["piecewise_observation_replay_count"],
                "stable_candidates": output["visually_stable_delivered_stone_candidate_count"],
                "simulation_ready": output["physics_simulation_ready_count"],
            }
        )
    )


if __name__ == "__main__":
    main()
