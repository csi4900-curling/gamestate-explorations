"""Add panel-aware shared-rink coordinates to a directional event aggregate.

Reads the frozen aggregate produced after the observation stage and writes a new
file; the input is never modified. Every mapped sample records both the raw
ice-plane position and the conditional height-adjusted position, plus the panel
and role used for the transform. Cross-view links gain the unobserved spatial
gap and an explicit plausibility diagnostic.

This is post-processing. It does not fit calibration, change handoff selection,
interpolate the unobserved middle, or establish physical identity.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path

from prototype.rink_coordinates import (
    MAX_PLAUSIBLE_SPEED_M_S,
    TEE_DISTANCE_M,
    handoff_from_rink,
    rink_position,
)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def panel_of(segment):
    camera = segment.get("camera")
    if camera == "left_split":
        return "left"
    if camera == "right_split":
        return "right"
    raise ValueError(f"Unknown segment camera: {camera!r}")


def map_sample(sample, *, panel, role, hog_y_m, lateral_sign, tee_distance):
    ice = sample.get("top_view_m")
    height = sample.get("conditional_height_adjusted_position_m")
    mapped = dict(sample)
    mapped["rink_panel"] = panel
    mapped["rink_role"] = role
    mapped["rink_ice_plane_m"] = (
        rink_position(ice, panel=panel, role=role, hog_y_m=hog_y_m,
                      lateral_sign=lateral_sign, tee_distance=tee_distance)
        if ice is not None else None
    )
    mapped["rink_height_adjusted_m"] = (
        rink_position(height, panel=panel, role=role, hog_y_m=hog_y_m,
                      lateral_sign=lateral_sign, tee_distance=tee_distance)
        if height is not None else None
    )
    if mapped["rink_height_adjusted_m"] is not None:
        mapped["rink_position_m"] = mapped["rink_height_adjusted_m"]
        mapped["rink_position_kind"] = "height_adjusted_estimate"
    elif mapped["rink_ice_plane_m"] is not None:
        # Preserve the raw projection as diagnostic evidence, not as a substitute
        # for the elevated detector feature's corrected metric position.
        mapped["rink_position_m"] = None
        mapped["rink_position_kind"] = "unavailable"
    else:
        mapped["rink_position_m"] = None
        mapped["rink_position_kind"] = "unavailable"
    return mapped


def first_last(samples, field="rink_position_m"):
    rows = [s for s in samples if s.get(field) is not None]
    return (rows[0], rows[-1]) if rows else (None, None)


def enrich(aggregate, *, aggregate_path=None, lateral_sign=1.0,
           tee_distance=TEE_DISTANCE_M,
           max_plausible_speed=MAX_PLAUSIBLE_SPEED_M_S):
    if aggregate.get("schema_version") != "learned-directional-event-track-bridge-development-v1":
        raise ValueError("Expected the directional event aggregate")
    provenance = aggregate.get("provenance") or {}
    hog_y_m = provenance.get("local_hog_y_m")
    if not isinstance(hog_y_m, dict) or set(hog_y_m) != {"left", "right"}:
        raise ValueError("Aggregate must record signed local_hog_y_m for both panels")
    if any(not isinstance(v, (int, float)) or not math.isfinite(v) or v == 0
           for v in hog_y_m.values()):
        raise ValueError("Signed hog coordinates must be finite and nonzero")

    events = []
    link_rows = []
    segment_count = 0
    sample_count = 0
    mapped_count = 0
    for event in aggregate["events"]:
        segments = []
        for segment in event["segments"]:
            panel = panel_of(segment)
            role = segment.get("role")
            mapped_segment = {k: v for k, v in segment.items() if k != "geometry_samples"}
            mapped_segment["rink_panel"] = panel
            mapped_segment["rink_role"] = role
            if role not in ("departure", "receiving"):
                mapped_segment["rink_coordinate_status"] = "unresolved_role"
                samples = [dict(s, rink_position_m=None,
                                rink_position_kind="unresolved_role",
                                rink_panel=panel, rink_role=role)
                           for s in segment.get("geometry_samples", [])]
            else:
                samples = [map_sample(s, panel=panel, role=role, hog_y_m=hog_y_m,
                                      lateral_sign=lateral_sign,
                                      tee_distance=tee_distance)
                           for s in segment.get("geometry_samples", [])]
                mapped_segment["rink_coordinate_status"] = (
                    "mapped_height_adjusted" if any(
                        s.get("rink_height_adjusted_m") is not None for s in samples)
                    else "mapped_ice_plane" if any(
                        s.get("rink_ice_plane_m") is not None for s in samples)
                    else "no_local_position"
                )
            first, last = first_last(samples)
            mapped_segment["geometry_samples"] = samples
            mapped_segment["rink_sample_count"] = sum(
                1 for s in samples if s.get("rink_position_m") is not None)
            mapped_segment["rink_first_m"] = first["rink_position_m"] if first else None
            mapped_segment["rink_last_m"] = last["rink_position_m"] if last else None
            mapped_segment["rink_first_time_s"] = first["time_s"] if first else None
            mapped_segment["rink_last_time_s"] = last["time_s"] if last else None
            mapped_segment["physical_identity_verified"] = False
            segment_count += 1
            sample_count += len(samples)
            mapped_count += mapped_segment["rink_sample_count"]
            segments.append(mapped_segment)

        by_id = {s["segment_id"]: s for s in segments}
        links = []
        for link in event.get("cross_view_links", []):
            departure = by_id.get(link["departure_segment"])
            receiving = by_id.get(link["receiving_segment"])
            if not departure or not receiving:
                links.append({**link, "spatial_consistency": "missing_segment"})
                continue
            da = [s for s in departure["geometry_samples"]
                  if s.get("rink_position_m") is not None]
            rb = [s for s in receiving["geometry_samples"]
                  if s.get("rink_position_m") is not None]
            if not da or not rb:
                links.append({**link, "spatial_consistency": "missing_rink_position"})
                continue
            # Both samples are already in the shared rink frame.
            diagnostic = handoff_from_rink(
                da[-1]["rink_position_m"], rb[0]["rink_position_m"],
                departure_time_s=da[-1]["time_s"],
                receiving_time_s=rb[0]["time_s"],
                max_plausible_speed=max_plausible_speed,
            )
            links.append({**link, **diagnostic})
            link_rows.append(links[-1])
        mapped_event = {k: v for k, v in event.items() if k not in ("segments", "cross_view_links")}
        mapped_event["segments"] = segments
        mapped_event["cross_view_links"] = links
        events.append(mapped_event)

    status_counts = {}
    for link in link_rows:
        status_counts[link["spatial_consistency"]] = status_counts.get(
            link["spatial_consistency"], 0) + 1
    gaps = [l["gap_m"] for l in link_rows if l.get("gap_m") is not None]
    speeds = [l["implied_speed_m_s"] for l in link_rows
              if l.get("implied_speed_m_s") is not None]
    result = {
        "schema_version": "directional-event-track-bridge-rink-v1",
        "source_interval_s": aggregate.get("source_interval_s"),
        "context": aggregate.get("context"),
        "events": events,
        "camera_crossings": aggregate.get('camera_crossings',[]),
        "scope": aggregate.get("scope"),
        "physical_identity_verified": False,
        "handoff_development_enabled": aggregate.get("handoff_development_enabled"),
        "rink_coordinate_system": {
            "origin": "delivery-end tee",
            "+y": "toward the receiving end",
            "+x": "image right, same direction for both panels (assumed)",
            "tee_distance_m": tee_distance,
            "unit": "metres",
            "not_canonical_throwing_orientation": True,
        },
        "rink_transform": {
            "method": "panel-aware signed-hog transform",
            "module": "prototype/rink_coordinates.py",
            "code_sha256": digest(Path(__file__).resolve().parents[1] / "rink_coordinates.py"),
            "hog_y_m": hog_y_m,
            "lateral_sign": lateral_sign,
            "tee_distance_m": tee_distance,
            "max_plausible_speed_m_s": max_plausible_speed,
            "assumptions": [
                "Role is the per-event observed motion role already in the aggregate; it is not re-inferred here.",
                "Lateral handedness is a recorded assumption; the handoff lateral gap was lower without a flip.",
                "Height-adjusted positions use the existing conditional body-centre height correction; they are estimates, not measured stone centres.",
                "The unobserved middle of the sheet is a gap; no interpolation is inserted.",
                "A plausible spatial gap does not establish physical identity.",
            ],
        },
        "event_colour": aggregate.get("event_colour"),
        "handoff_colour": aggregate.get("handoff_colour"),
        "summary": {
            "events": len(events),
            "segments": segment_count,
            "geometry_samples": sample_count,
            "mapped_geometry_samples": mapped_count,
            "cross_view_links": len(link_rows),
            "link_status_counts": status_counts,
            "gap_m_median": sorted(gaps)[len(gaps) // 2] if gaps else None,
            "gap_m_max": max(gaps) if gaps else None,
            "implied_speed_m_s_median": sorted(speeds)[len(speeds) // 2] if speeds else None,
            "implied_speed_m_s_max": max(speeds) if speeds else None,
        },
        "provenance": {
            "input_aggregate": str(Path(aggregate_path).resolve()) if aggregate_path else None,
            "input_aggregate_sha256": digest(aggregate_path) if aggregate_path else None,
            "source_sha256": (aggregate.get("context") or {}).get("source_sha256"),
            "postprocessing": True,
            "inference_changed": False,
            "frozen_run_modified": False,
        },
    }
    fragments=aggregate.get('unresolved_camera_fragments',[])
    if fragments:
        # Use the identical transform/measurement semantics for standalone
        # observations. They remain outside the physical-event candidate list.
        fragment_input={**aggregate,'events':fragments,'unresolved_camera_fragments':[]}
        mapped=enrich(fragment_input,aggregate_path=aggregate_path,lateral_sign=lateral_sign,
                      tee_distance=tee_distance,max_plausible_speed=max_plausible_speed)
        result['unresolved_camera_fragments']=mapped['events']
    else:result['unresolved_camera_fragments']=[]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aggregate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary", type=Path)
    parser.add_argument("--lateral-sign", type=float, default=1.0)
    parser.add_argument("--tee-distance", type=float, default=TEE_DISTANCE_M)
    parser.add_argument("--max-plausible-speed", type=float,
                        default=MAX_PLAUSIBLE_SPEED_M_S)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("Output exists; preserve the previous run")
    aggregate = json.loads(args.aggregate.read_text())
    result = enrich(aggregate, aggregate_path=args.aggregate,
                    lateral_sign=args.lateral_sign,
                    tee_distance=args.tee_distance,
                    max_plausible_speed=args.max_plausible_speed)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    summary_path = args.summary or args.output.with_suffix(".summary.json")
    summary_path.write_text(json.dumps({
        "summary": result["summary"],
        "rink_transform": result["rink_transform"],
        "provenance": result["provenance"],
    }, indent=2, allow_nan=False) + "\n")
    print(json.dumps(result["summary"]))


if __name__ == "__main__":
    main()
