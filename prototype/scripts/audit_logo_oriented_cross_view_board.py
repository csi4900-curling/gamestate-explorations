"""Source-only board overlap after button-emblem orientation, no official board."""

from hashlib import sha256
import json
from pathlib import Path
import sys
from statistics import median

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.scripts.audit_swiss_end2_wide_contact_transfer import compare_source_boards

BASE = ROOT / "validation/official-shot-sequence"
LOGO = BASE / "button-logo-cross-view-orientation-development.json"
CHINA_CONTACT = BASE / "china-end2-wide-body-contact-diagnostic.json"
CHINA_CLOSE = BASE / "china-end2-adjacent-video-boards-first.json"
SWISS_WIDE = BASE / "swiss-end2-wide-blue-ring-v2-development.json"
SWISS_CLOSE = BASE / "swiss-end2-adjacent-video-boards-first.json"
OUTPUT = BASE / "button-logo-oriented-cross-view-boards-development.json"


def digest(path):
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def oriented_points(contacts, ellipses, sign):
    cx = median(row["center_px"][0] for row in ellipses)
    cy = median(row["center_px"][1] for row in ellipses)
    rx = median(max(row["axis_lengths_px"]) / 2 for row in ellipses)
    ry = median(min(row["axis_lengths_px"]) / 2 for row in ellipses)
    return [{"colour": row["colour"],
             "canonical_lateral_house_radii": round(
                 sign * (row["contact_pixel_center"][0] - cx) / rx, 4),
             "longitudinal_house_radii": round(
                 sign * (row["contact_pixel_center"][1] - cy) / ry, 4),
             "source_view": "wide_body_contact"}
            for row in contacts]


def union_with_source_overlap(wide, overhead, overlap):
    used_wide = set()
    for match in overlap["matches"]:
        colour_indices = [index for index, stone in enumerate(wide)
                          if stone["colour"] == match["colour"]]
        used_wide.add(colour_indices[match["wide_index_within_colour"]])
    fused = [{**row, "source_view": "overhead_partial_board"} for row in overhead]
    fused.extend(row for index, row in enumerate(wide) if index not in used_wide)
    return fused


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first oriented board handoff")
    logo = json.loads(LOGO.read_text())
    china_contact = json.loads(CHINA_CONTACT.read_text())
    china_close = json.loads(CHINA_CLOSE.read_text())
    swiss_wide = json.loads(SWISS_WIDE.read_text())
    swiss_close = json.loads(SWISS_CLOSE.read_text())
    inputs = {
        "china_end2_s12": {
            "source_sha256": china_contact["source_sha256"],
            "shot_id": "PREL000102-E02-S12",
            "contacts": china_contact["contacts"],
            "ellipses": [row["ellipse"] for row in
                         json.loads((BASE / "china-end2-wide-perspective-cap-evidence-development.json")
                                    .read_text())["frames"]],
            "overhead": next(row["stable_partial_board"] for row in china_close["rows"]
                             if row["shot_id"] == "PREL000102-E02-S12"),
        },
        "swiss_end2_s13": {
            "source_sha256": swiss_wide["source_sha256"],
            "shot_id": "PREL000101-E02-S13",
            "contacts": [{"colour": row["colour"],
                          "contact_pixel_center": row["pixel_center"]}
                         for row in next(row["stable_contact_tracks"]
                                         for row in swiss_wide["rows"]
                                         if row["shot_id"] == "PREL000101-E02-S13")],
            "ellipses": [row["ellipse"] for row in
                         next(row["wide_frames"] for row in swiss_wide["rows"]
                              if row["shot_id"] == "PREL000101-E02-S13")],
            "overhead": next(row["stable_partial_board"] for row in swiss_close["rows"]
                             if row["shot_id"] == "PREL000101-E02-S13"),
        },
    }
    if (china_contact["source_sha256"] != china_close["source_sha256"] or
            swiss_wide["source_sha256"] != swiss_close["source_sha256"]):
        raise ValueError("Cross-view source fingerprint mismatch")
    output_rows = []
    for case in logo["cases"]:
        data = inputs[case["name"]]
        if case["source_sha256"] != data["source_sha256"]:
            raise ValueError("Logo and board source mismatch")
        rotation = case["unanimous_relative_rotation_degrees"]
        if rotation not in (0, 180):
            raise ValueError("Source logo did not resolve view orientation")
        sign = 1 if rotation == 0 else -1
        wide_points = oriented_points(data["contacts"], data["ellipses"], sign)
        overhead = data["overhead"]
        overlap = compare_source_boards(wide_points, overhead)
        fused = union_with_source_overlap(wide_points, overhead, overlap)
        output_rows.append({
            "case": case["name"], "source_sha256": data["source_sha256"],
            "shot_id": data["shot_id"],
            "logo_selected_relative_rotation_degrees": rotation,
            "orientation_source": "painted_button_logo_only",
            "wide_source_points": wide_points,
            "overhead_source_points": overhead,
            "source_only_same_colour_overlap": overlap,
            "provisional_union_points": fused,
            "physical_stone_identities_verified": False,
            "board_completeness_verified_from_video": False,
            "simulation_ready": False,
        })
    output = {
        "status": "selected_source_only_logo_oriented_cross_view_board_evidence_not_state_export",
        "logo_artifact_sha256": digest(LOGO),
        "china_contact_sha256": digest(CHINA_CONTACT),
        "china_close_sha256": digest(CHINA_CLOSE),
        "swiss_wide_sha256": digest(SWISS_WIDE),
        "swiss_close_sha256": digest(SWISS_CLOSE),
        "runner_sha256": digest(Path(__file__)),
        "rows": output_rows,
        "limitations": [
            "Both examples were selected after development-source inspection.",
            "The logo cue determines relative rotation in these two Beijing 2022 handoffs only.",
            "Ellipse normalization and grey body-bottom points are not metric ice-plane calibration.",
            "Stone overlap is same-colour proximity, not verified physical identity.",
            "Counter windows and time gaps do not prove an unchanged settled board.",
            "No official diagram position is read and no state is simulation-ready.",
        ],
    }
    OUTPUT.write_text(json.dumps(output, indent=2) + "\n")
    print([(row["case"], len(row["wide_source_points"]),
            row["source_only_same_colour_overlap"]["matched_count"],
            len(row["provisional_union_points"])) for row in output_rows])


if __name__ == "__main__":
    main()
