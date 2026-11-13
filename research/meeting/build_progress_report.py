"""Build an offline, source-linked report for the 9 October team meeting."""

from base64 import b64encode
from pathlib import Path
import json


ROOT = Path(__file__).resolve().parents[2]
MEETING = Path(__file__).resolve().parent
TRANSFER = (
    ROOT / "validation/throw-event-benchmark/paralympics-2022-canada-norway/FIRST-TRANSFER.json"
)
DIAGNOSTIC = (
    ROOT
    / "validation/curlobserver-learned-probe/canada-norway-full-transfer/delivery-ice-cap-diagnostic.json"
)
HELD_END7 = (
    ROOT
    / "validation/curlobserver-learned-probe/cap-patch-crossmatch-v1/norway-end7-held-origin-counter-proxy-first.json"
)
GATE_END8 = (
    ROOT
    / "validation/curlobserver-learned-probe/cap-patch-crossmatch-v1/norway-end8-dual-gate-counter-proxy-first.json"
)
NONORIGIN = ROOT / "validation/curlobserver-learned-probe/cap-patch-crossmatch-v1"
NONORIGIN_CHINA = NONORIGIN / "china-nonorigin-phase-v2-first.json"
NONORIGIN_CHINA_OVERLAP = NONORIGIN / "china-nonorigin-phase-v2-overlap-postscore.json"
NONORIGIN_CHINA_MOTION = NONORIGIN / "china-nonorigin-camera-relative-postscore.json"
NONORIGIN_CHINA_TRACK = NONORIGIN / "china-nonorigin-track-continuity-postscore.json"
NONORIGIN_TRACK_CROSS = NONORIGIN / "nonorigin-track-continuity-development.json"
CAP_TRACK_FULL = NONORIGIN / "china-cap-track-quality-full-v2-first.json"
CAP_TRACK_OVERLAP = NONORIGIN / "china-cap-track-quality-overlap-v2-postscore.json"
COLOUR_PROVENANCE = (
    ROOT
    / "validation/curlobserver-learned-probe/china-full-transfer/event-colour-provenance-v1.json"
)
EVENT_GROUNDING = (
    ROOT
    / "validation/curlobserver-learned-probe/china-full-transfer/event-grounding-envelope-v1.json"
)
CHINA_POSSIBLE_EDITS = (
    ROOT / "validation/curlobserver-learned-probe/china-full-transfer/possible-edits-v1.json"
)
SWISS_POSSIBLE_EDITS = (
    ROOT / "validation/curlobserver-learned-probe/swiss-full-transfer/possible-edits-v1.json"
)
NORWAY_POSSIBLE_EDITS = (
    ROOT
    / "validation/curlobserver-learned-probe/canada-norway-full-transfer/possible-edits-v1.json"
)
SLOVAKIA_POSSIBLE_EDITS = (
    ROOT / "validation/curlobserver-learned-probe/slovakia-full-transfer/possible-edits-v1.json"
)
EDIT_EVENT_OVERLAP = (
    ROOT
    / "validation/curlobserver-learned-probe/china-full-transfer/possible-edit-event-overlap-postscan.json"
)
EDIT_REGISTRATION = (
    ROOT / "validation/curlobserver-learned-probe/possible-edit-registration-postscan.json"
)
TEMPORAL_EDIT_ARTIFACTS = [
    ROOT / f"validation/curlobserver-learned-probe/{folder}/possible-edit-temporal-v1.json"
    for folder in (
        "china-full-transfer",
        "swiss-full-transfer",
        "canada-norway-full-transfer",
        "slovakia-full-transfer",
    )
]
EVENT_BOARD = (
    ROOT / "validation/official-shot-sequence/pwg2022-provisional-event-board-evidence.json"
)
EVENT_BOARD_V2 = (
    ROOT / "validation/official-shot-sequence/pwg2022-provisional-event-board-evidence-v2.json"
)
ADJACENT_SCORE = (
    ROOT / "validation/official-shot-sequence/swiss-end2-adjacent-board-comparison-development.json"
)
ADJACENT_CHINA_SCORE = (
    ROOT / "validation/official-shot-sequence/china-end2-adjacent-board-comparison-first.json"
)
WIDE_CHINA = (
    ROOT
    / "validation/official-shot-sequence/china-end2-wide-perspective-cap-evidence-development.json"
)
WIDE_AFFINE = (
    ROOT / "validation/official-shot-sequence/china-end2-wide-affine-projection-diagnostic.json"
)
WIDE_CONTACT = (
    ROOT / "validation/official-shot-sequence/china-end2-wide-body-contact-diagnostic.json"
)
WIDE_FUSION = ROOT / "validation/official-shot-sequence/china-end2-s11-wide-fusion-development.json"
WIDE_SWISS = ROOT / "validation/official-shot-sequence/swiss-end2-wide-contact-first-transfer.json"
WIDE_SWISS_V2 = (
    ROOT / "validation/official-shot-sequence/swiss-end2-wide-blue-ring-v2-development.json"
)
WIDE_SLOVAKIA = (
    ROOT / "validation/official-shot-sequence/slovakia-wide-blue-ring-first-transfer.json"
)
BUTTON_LOGO = (
    ROOT / "validation/official-shot-sequence/button-logo-cross-view-orientation-development.json"
)
LOGO_BOARDS = (
    ROOT
    / "validation/official-shot-sequence/button-logo-oriented-cross-view-boards-development.json"
)
LOGO_GATE = (
    ROOT
    / "validation/curlobserver-learned-probe/cap-patch-crossmatch-v1/norway-end8-logo-gate-coverage-first.json"
)
CHINA_BOARD_EVENT_COVERAGE = (
    ROOT / "validation/official-shot-sequence/china-board-event-coverage-v1.json"
)
HELD_RESCUE = (
    ROOT / "validation/official-shot-sequence/pwg2022-held-origin-counter-rescue-development.json"
)
TRAVEL_RESCUE = (
    ROOT / "validation/official-shot-sequence/pwg2022-cap-fusion-travel-rescue-development.json"
)
TRAVEL_RECONCILIATION = (
    ROOT / "validation/official-shot-sequence/pwg2022-travel-origin-reconciliation-development.json"
)
CAP_VISUAL_RELINK = (
    ROOT / "validation/official-shot-sequence/pwg2022-cap-visual-counter-links-development.json"
)
PROVISIONAL_UNION = (
    ROOT
    / "validation/official-shot-sequence/pwg2022-provisional-event-evidence-union-development.json"
)
CHINA_BOARD_UNION = (
    ROOT / "validation/official-shot-sequence/china-board-event-union-handoff-development.json"
)
FULL_REVIEW_SEGMENTS = (
    ROOT
    / "validation/official-shot-sequence/pwg2022-full-match-event-review-segments-development.json"
)
ICE_TIEBREAK = (
    ROOT
    / "validation/official-shot-sequence/pwg2022-ambiguous-counter-ice-tiebreak-development.json"
)
ICE_TIEBREAK_NORWAY = (
    ROOT / "validation/official-shot-sequence/norway-ambiguous-counter-ice-tiebreak-first.json"
)
CHRONOLOGY_TIEBREAK = (
    ROOT / "validation/official-shot-sequence/pwg2022-counter-chronology-tiebreak-development.json"
)
SEQUENCE_ORDER = (
    ROOT / "validation/official-shot-sequence/pwg2022-counter-sequence-order-development.json"
)
ORDER_COLOUR_SCREEN = (
    ROOT / "validation/official-shot-sequence/pwg2022-counter-order-colour-screen-development.json"
)
SLOVAKIA_HELD_COLOUR = (
    ROOT / "validation/official-shot-sequence/slovakia-ambiguous-held-colour-development.json"
)
SLOVAKIA_RELEASE_PASSAGES = (
    ROOT / "validation/official-shot-sequence/slovakia-ambiguous-release-passages-development.json"
)
COUNTER_SAMPLE_SUPPORT = (
    ROOT / "validation/official-shot-sequence/pwg2022-counter-sample-support-development.json"
)
SLOVAKIA_RELEASE_COVERAGE = (
    ROOT
    / "validation/official-shot-sequence/slovakia-provisional-release-coverage-development.json"
)
SWISS_RELEASE_TRANSFER = (
    ROOT / "validation/official-shot-sequence/swiss-provisional-release-transfer-first.json"
)
CHINA_RELEASE_TRANSFER = (
    ROOT / "validation/official-shot-sequence/china-provisional-release-transfer-first.json"
)
CROSS_VIEW_SOURCE_COLOUR = (
    ROOT
    / "validation/official-shot-sequence/pwg2022-cross-view-source-colour-handoff-development.json"
)
TWO_VIEW_TEMPORAL = (
    ROOT / "validation/official-shot-sequence/pwg2022-two-view-temporal-handoff-development.json"
)
S593_BACKGROUND = (
    ROOT / "validation/official-shot-sequence/china-s593-background-registration-development.json"
)
RELEASE_BOARD_HANDOFF = (
    ROOT / "validation/official-shot-sequence/pwg2022-release-to-board-handoff-development.json"
)
HELD_SHOT_BOARD_HANDOFF = (
    ROOT / "validation/official-shot-sequence/pwg2022-held-shot-release-to-board-development.json"
)
SHOT_SCOPED_RELEASE = (
    ROOT / "validation/official-shot-sequence/pwg2022-shot-scoped-release-cues-development.json"
)
OUTSIDE_UNION_CUES = (
    ROOT
    / "validation/official-shot-sequence/pwg2022-origin-shots-outside-union-cues-development.json"
)
OUTSIDE_UNION_PROPOSALS = (
    ROOT
    / "validation/official-shot-sequence/pwg2022-outside-union-release-rescue-proposals-development.json"
)
OUTSIDE_UNION_RECEIVING = (
    ROOT / "validation/official-shot-sequence/pwg2022-outside-union-receiving-view-development.json"
)
SOURCE_RESCUE_UNION_V2 = (
    ROOT
    / "validation/official-shot-sequence/pwg2022-provisional-event-evidence-union-v2-source-rescues-development.json"
)
SOURCE_RESCUE_REVIEW_V2 = (
    ROOT
    / "validation/official-shot-sequence/pwg2022-full-match-event-review-segments-v2-source-rescues-development.json"
)
EVENT_HANDOFF_V2 = (
    ROOT / "validation/official-shot-sequence/pwg2022-event-evidence-handoff-v2-development.json"
)
ALL_UNASSIGNED_SCAN = (
    ROOT
    / "validation/official-shot-sequence/pwg2022-all-unassigned-shots-source-scan-summary-development.json"
)
PREORIGIN_TRAVEL_RESCUE = (
    ROOT
    / "validation/official-shot-sequence/pwg2022-preorigin-travel-rescue-proposals-development.json"
)
PREORIGIN_UNION_V3 = (
    ROOT
    / "validation/official-shot-sequence/pwg2022-provisional-event-evidence-union-v3-preorigin-travel-development.json"
)
PREORIGIN_REVIEW_V3 = (
    ROOT
    / "validation/official-shot-sequence/pwg2022-full-match-event-review-segments-v3-preorigin-travel-development.json"
)
EVENT_HANDOFF_V3 = (
    ROOT / "validation/official-shot-sequence/pwg2022-event-evidence-handoff-v3-development.json"
)
COUNTER_SLOT_V3 = (
    ROOT / "validation/official-shot-sequence/pwg2022-v3-counter-slot-coverage-development.json"
)
KOREA_EVENTS = ROOT / "prototype/throw-analysis/evaluation.json"
KOREA_PREDICTIONS = ROOT / "prototype/throw-analysis/predictions.json"
KOREA_TRAJECTORY = ROOT / "prototype/trajectory-accuracy/results.json"
KOREA_SOURCE = ROOT / "prototype/throw-analysis/source.json"
SEQUENCE_V3 = (
    ROOT
    / "validation/official-shot-sequence/pwg2022-v3-official-sequence-diagnostic-development.json"
)
S593_SENSITIVITY = (
    ROOT
    / "validation/official-shot-sequence/china-s593-sequence-colour-sensitivity-development.json"
)
SEQUENCE_REVIEW_QUEUE = (
    ROOT / "validation/official-shot-sequence/pwg2022-v3-sequence-review-queue-development.json"
)
CHINA_E01_RECEIVING_GAP = (
    ROOT / "validation/official-shot-sequence/china-e01-s14-receiving-gap-development.json"
)
OUTPUT = ROOT / "supervisor-progress-2026-10-09.html"
ENGLISH_OUTPUT = ROOT / "supervisor-progress-2026-10-09.en.html"


def jpeg_data(path):
    return "data:image/jpeg;base64," + b64encode(path.read_bytes()).decode("ascii")


def png_data(path):
    return "data:image/png;base64," + b64encode(path.read_bytes()).decode("ascii")


def main():
    korea_events = json.loads(KOREA_EVENTS.read_text())
    korea_predictions = json.loads(KOREA_PREDICTIONS.read_text())
    korea_trajectory = json.loads(KOREA_TRAJECTORY.read_text())
    korea_source = json.loads(KOREA_SOURCE.read_text())
    if (
        korea_source["source_interval_s"] != [1650, 2760]
        or korea_predictions["source"] != "aWXo6XeUFQw"
        or len(korea_predictions["events"]) != 16
        or korea_events["all"]["true_positives"] != 16
        or korea_events["all"]["false_positives"] != 0
        or korea_events["all"]["misses"] != 0
        or korea_trajectory["moving_labels"]["matched_count"] != 4
        or not 1.15 < korea_trajectory["moving_labels"]["pixel_rmse"] < 1.17
        or korea_trajectory["physical_accuracy_measured"]
    ):
        raise ValueError("Canada–Korea case-study evidence changed: review the report")
    transfer = json.loads(TRANSFER.read_text())
    diagnostic = json.loads(DIAGNOSTIC.read_text())
    end2 = transfer["complete_counter_anchored_ends"]
    if len(end2) != 1 or end2[0]["end"] != 2:
        raise ValueError("Expected one complete counter-anchored end, end 2")
    score = end2[0]["cap_only_score"]
    if (
        transfer["official_shot_count"] != 128
        or transfer["candidate_count"] != 142
        or transfer["clean_counter_anchor_count"] != 100
        or score["matched_count"] != 15
        or score["known_colour_conflict_count"] != 4
        or diagnostic["scanned_window_count"] != 146
    ):
        raise ValueError("Evidence changed: review the report before rebuilding")
    original_cap = json.loads(
        (
            ROOT
            / "validation/curlobserver-learned-probe/canada-norway-full-transfer/two-shot-cap.json"
        ).read_text()
    )
    spatial = {row["shot_id"]: row for row in diagnostic["rows"]}
    confirmed = [
        row for row in original_cap["decisions"] if row["status"] == "corroborated_candidate"
    ]
    spatial_any = sum(bool(spatial[row["shot_id"]]["supported_colours"]) for row in confirmed)
    if len(confirmed) != 114 or spatial_any != 52:
        raise ValueError("Spatial diagnostic changed: review the report")
    held_end7 = json.loads(HELD_END7.read_text())
    held_score = held_end7["score"]
    if (
        held_end7["end"] != 7
        or held_score["visual_candidate_count"] != 14
        or held_score["matched_count"] != 10
        or held_score["clean_counter_count"] != 12
        or held_score["known_colour_match_count"] != 10
        or held_score["known_colour_conflict_count"] != 0
    ):
        raise ValueError("End-seven evidence changed: review the report")
    gate_end8 = json.loads(GATE_END8.read_text())
    gate_score = gate_end8["score"]
    if (
        gate_end8["end"] != 8
        or gate_score["visual_candidate_count"] != 16
        or gate_score["matched_count"] != 8
        or gate_score["clean_counter_count"] != 9
        or gate_score["known_colour_match_count"] != 7
        or gate_score["known_colour_conflict_count"] != 1
    ):
        raise ValueError("End-eight evidence changed: review the report")
    nonorigin_counts = [
        json.loads((NONORIGIN / name).read_text())["candidate_count"]
        for name in (
            "norway-end7-nonorigin-continuity-development.json",
            "norway-end8-nonorigin-continuity-first.json",
            "slovakia-nonorigin-continuity-first.json",
            "swiss-nonorigin-continuity-first.json",
        )
    ]
    if nonorigin_counts != [1, 0, 0, 4]:
        raise ValueError("Non-origin transfer evidence changed: review the report")
    relative = json.loads(
        (NONORIGIN / "nonorigin-camera-relative-audit-development.json").read_text()
    )
    relative_rows = {row["shot_id"]: row for row in relative["rows"]}
    if (
        len(relative_rows) != 5
        or relative_rows["S465"]["reliable_over_10px_count"] != 1
        or relative_rows["S171"]["reliable_over_10px_count"] != 1
        or relative_rows["S404"]["reliable_over_10px_count"] != 0
        or relative_rows["S322"]["reliable_pair_count"] != 0
        or relative_rows["S566"]["pair_count"] != 0
    ):
        raise ValueError("Camera-relative diagnostic changed: review the report")
    phase_v2 = json.loads((NONORIGIN / "nonorigin-phase-v2-development.json").read_text())
    if [(row["case"], row["v1_count"], row["v2_count"]) for row in phase_v2["cases"]] != [
        ("norway-end7", 1, 1),
        ("norway-end8", 0, 0),
        ("slovakia", 0, 0),
        ("swiss", 4, 1),
    ]:
        raise ValueError("Phase-aware development evidence changed: review the report")
    china_nonorigin = json.loads(NONORIGIN_CHINA.read_text())
    china_nonorigin_overlap = json.loads(NONORIGIN_CHINA_OVERLAP.read_text())
    china_motion = json.loads(NONORIGIN_CHINA_MOTION.read_text())
    if (
        china_nonorigin["shot_count"] != 630
        or china_nonorigin["candidate_count"] != 2
        or [row["shot_id"] for row in china_nonorigin["candidates"]] != ["S123", "S519"]
        or china_nonorigin_overlap["fallback_candidate_count"] != 2
        or china_nonorigin_overlap["novel_camera_shot_count"] != 0
        or china_nonorigin_overlap["linked_counter_colour_conflict_count"] != 1
    ):
        raise ValueError("China non-origin fallback transfer changed: review the report")
    motion_rows = {row["shot_id"]: row for row in china_motion["rows"]}
    if (
        set(motion_rows) != {"S123", "S519"}
        or motion_rows["S123"]["top_transit_camera_motion"][0]["reliable_over_10px_count"] != 2
        or motion_rows["S519"]["top_transit_camera_motion"][0]["reliable_pair_count"] != 0
    ):
        raise ValueError("China camera-relative diagnostic changed: review the report")
    china_track = json.loads(NONORIGIN_CHINA_TRACK.read_text())
    track_rows = {row["shot_id"]: row for row in china_track["rows"]}
    if (
        set(track_rows) != {"S123", "S519"}
        or track_rows["S123"]["transit_tracks"][0]["step_shape"]["largest_step_fraction"] != 0.969
        or track_rows["S123"]["top_frame_changes"][0]["time_s"] != 1606.0
        or track_rows["S519"]["top_frame_changes"][0]["time_s"] != 7029.4
    ):
        raise ValueError("China track-continuity diagnostic changed: review the report")
    cross_track = json.loads(NONORIGIN_TRACK_CROSS.read_text())
    cross_rows = {row["shot_id"]: row for row in cross_track["rows"]}
    if (
        set(cross_rows) != {"S465", "S171", "S322", "S404", "S566"}
        or cross_rows["S404"]["step_shape"]["steps_over_5px"] != 11
        or cross_rows["S404"]["max_reliable_camera_residual_px"] != 7.297
    ):
        raise ValueError("Cross-recording track diagnostic changed: review the report")
    cap_track_full = json.loads(CAP_TRACK_FULL.read_text())
    cap_track_overlap = json.loads(CAP_TRACK_OVERLAP.read_text())
    if (
        len(cap_track_full["rows"]) != 102
        or cap_track_overlap["quality_counts"].get("combined_cue_supported") != 15
        or cap_track_overlap["quality_counts"].get("abstain_unknown_colour") != 42
        or cap_track_overlap["known_colour_counter_associated_window_count"] != 43
        or cap_track_overlap["combined_supported_counter_associated_window_count"] != 12
    ):
        raise ValueError("Full China track-quality coverage changed: review the report")
    colour_provenance = json.loads(COLOUR_PROVENANCE.read_text())
    if colour_provenance["event_count"] != 112 or colour_provenance["basis_counts"] != {
        "counter_with_ambiguous_visual": 39,
        "counter_without_corroborated_visual": 10,
        "unresolved_ambiguous_visual": 3,
        "visual_and_counter_agree": 43,
        "visual_only": 17,
    }:
        raise ValueError("China colour provenance changed: review the report")
    event_grounding = json.loads(EVENT_GROUNDING.read_text())
    if (
        event_grounding["event_count"] != 112
        or event_grounding["camera_continuity_counts"]
        != {
            "no_proposed_internal_edit": 77,
            "possible_edit_crosses_cap_track": 21,
            "possible_edit_without_crossing_cap_track": 14,
        }
        or any(row["simulation_handoff"]["simulation_ready"] for row in event_grounding["events"])
    ):
        raise ValueError("China event grounding changed: review the report")
    china_edits = json.loads(CHINA_POSSIBLE_EDITS.read_text())
    swiss_edits = json.loads(SWISS_POSSIBLE_EDITS.read_text())
    edit_overlap = json.loads(EDIT_EVENT_OVERLAP.read_text())
    if (
        china_edits["reproduced_hard_cut_count"] != 629
        or china_edits["possible_edits_outside_hard_cuts_count"] != 58
        or china_edits["affected_existing_camera_shot_count"] != 55
        or swiss_edits["reproduced_hard_cut_count"] != 603
        or swiss_edits["possible_edits_outside_hard_cuts_count"] != 6
        or edit_overlap["affected_event_candidate_shot_count"] != 35
        or edit_overlap["possible_edit_crossing_cap_track_count"] != 29
    ):
        raise ValueError("Possible-edit coverage changed: review the report")
    norway_edits = json.loads(NORWAY_POSSIBLE_EDITS.read_text())
    slovakia_edits = json.loads(SLOVAKIA_POSSIBLE_EDITS.read_text())
    temporal_edits = [json.loads(path.read_text()) for path in TEMPORAL_EDIT_ARTIFACTS]
    if (
        norway_edits["reproduced_hard_cut_count"] != 708
        or norway_edits["possible_edits_outside_hard_cuts_count"] != 10
        or slovakia_edits["reproduced_hard_cut_count"] != 494
        or slovakia_edits["possible_edits_outside_hard_cuts_count"] != 17
        or [row["counts"]["isolated_spike"] for row in temporal_edits] != [55, 3, 7, 13]
    ):
        raise ValueError("Possible-edit temporal transfer changed: review the report")
    edit_registration = json.loads(EDIT_REGISTRATION.read_text())
    if [
        (row["source"], row["possible_edit_count"], row["reliable_registration_count"])
        for row in edit_registration["sources"]
    ] != [("china", 58, 0), ("swiss", 6, 0)]:
        raise ValueError("Possible-edit registration audit changed: review the report")
    event_board = json.loads(EVENT_BOARD.read_text())
    if (
        event_board["link_count"] != 7
        or event_board["unique_shared_counter_count"] != 7
        or event_board["stone_observation_count"] != 22
        or any(row["simulation_ready"] for row in event_board["links"])
    ):
        raise ValueError("Event-board handoff changed: review the report")
    event_board_v2 = json.loads(EVENT_BOARD_V2.read_text())
    adjacent_score = json.loads(ADJACENT_SCORE.read_text())
    china_score = json.loads(ADJACENT_CHINA_SCORE.read_text())
    if (
        event_board_v2["link_count"] != 9
        or event_board_v2["stone_observation_count"] != 26
        or event_board_v2["adjacent_partial_transition_count"] != 2
        or any(row["simulation_ready"] for row in event_board_v2["links"])
        or adjacent_score["scanned_shot_count"] != 5
        or adjacent_score["boards_with_stones"] != 3
        or adjacent_score["complete_diagram_match_count"] != 3
        or china_score["scanned_shot_count"] != 5
        or china_score["boards_with_stones"] != 2
        or china_score["complete_diagram_match_count"] != 0
    ):
        raise ValueError("Adjacent board evidence changed: review the report")
    wide_china = json.loads(WIDE_CHINA.read_text())
    if (
        len(wide_china["frames"]) != 4
        or sum(row["ellipse"] is not None for row in wide_china["frames"]) != 4
        or [row["colour"] for row in wide_china["stable_image_caps"]] != ["red", "red", "yellow"]
    ):
        raise ValueError("Wide-view China evidence changed: review the report")
    affine = json.loads(WIDE_AFFINE.read_text())
    if (
        len(affine["alternatives"]) != 4
        or max(row["matched_within_0_25_house_radii"] for row in affine["alternatives"]) != 1
        or min(row["forced_mean_error_house_radii"] for row in affine["alternatives"]) < 0.4
    ):
        raise ValueError("Wide-view affine diagnostic changed: review the report")
    contact = json.loads(WIDE_CONTACT.read_text())
    contact_by_sign = {
        row["lateral_sign"]: row for row in contact["postscore_lateral_alternatives"]
    }
    if (
        len(contact["contacts"]) != 3
        or contact["source_only_longitudinal_sign"] != -1
        or contact_by_sign[-1]["strict_postscore"]["matched_count"] != 3
        or contact_by_sign[1]["strict_postscore"]["matched_count"] != 2
        or not 0.13
        < contact_by_sign[-1]["strict_postscore"]["mean_matched_distance_house_radii"]
        < 0.16
    ):
        raise ValueError("Wide-view body-contact diagnostic changed: review the report")
    fusion = json.loads(WIDE_FUSION.read_text())
    if (
        len(fusion["stable_wide_contacts"]) != 2
        or len(fusion["source_only_fused_points"]) != 3
        or fusion["postscore_comparison"]["matched_count"] != 3
        or not 0.12 < fusion["postscore_comparison"]["mean_matched_distance_house_radii"] < 0.14
    ):
        raise ValueError("Adjacent wide-view fusion changed: review the report")
    swiss_wide = json.loads(WIDE_SWISS.read_text())
    swiss_wide_rows = {row["shot_id"]: row for row in swiss_wide["rows"]}
    swiss_s13 = swiss_wide_rows["PREL000101-E02-S13"]
    if (
        len(swiss_wide_rows) != 5
        or [
            (row["wide_ellipse_frame_count"], len(row["stable_contact_tracks"]))
            for row in swiss_wide["rows"]
        ]
        != [(0, 0), (3, 0), (1, 0), (3, 1), (0, 0)]
        or len(swiss_s13["overhead_partial_board"]) != 2
        or sorted(
            (a["lateral_sign"], a["longitudinal_sign"])
            for a in swiss_s13["source_only_orientation_alternatives"]
            if a["source_overlap"]["matched_count"] == 1
        )
        != [(-1, -1), (1, 1)]
    ):
        raise ValueError("Swiss wide-view transfer changed: review the report")
    swiss_v2 = json.loads(WIDE_SWISS_V2.read_text())
    swiss_v2_s13 = next(row for row in swiss_v2["rows"] if row["shot_id"] == "PREL000101-E02-S13")
    if len(swiss_v2_s13["stable_contact_tracks"]) != 2 or sorted(
        (a["lateral_sign"], a["longitudinal_sign"])
        for a in swiss_v2_s13["source_only_orientation_alternatives"]
        if a["source_overlap"]["matched_count"] == 2
    ) != [(-1, -1), (1, 1)]:
        raise ValueError("Swiss blue-ring revision changed: review the report")
    slovakia_wide = json.loads(WIDE_SLOVAKIA.read_text())
    if (
        len(slovakia_wide["rows"]) != 5
        or [row["wide_ellipse_frame_count"] for row in slovakia_wide["rows"]] != [0, 0, 1, 0, 1]
        or any(row["stable_contact_tracks"] for row in slovakia_wide["rows"])
    ):
        raise ValueError("Slovakia wide-view transfer changed: review the report")
    logo = json.loads(BUTTON_LOGO.read_text())
    if len(logo["cases"]) != 2 or [
        (
            row["resolved_pair_count"],
            len(row["cross_view_pairs"]),
            row["unanimous_relative_rotation_degrees"],
        )
        for row in logo["cases"]
    ] != [(12, 12, 180), (12, 12, 180)]:
        raise ValueError("Button-logo orientation evidence changed: review the report")
    logo_boards = json.loads(LOGO_BOARDS.read_text())
    if (
        len(logo_boards["rows"]) != 2
        or [
            (
                len(row["wide_source_points"]),
                row["source_only_same_colour_overlap"]["matched_count"],
                len(row["provisional_union_points"]),
            )
            for row in logo_boards["rows"]
        ]
        != [(3, 1, 3), (2, 2, 2)]
        or any(row["simulation_ready"] for row in logo_boards["rows"])
    ):
        raise ValueError("Logo-oriented board evidence changed: review the report")
    logo_gate = json.loads(LOGO_GATE.read_text())
    if (
        len(logo_gate["rows"]) != 19
        or any(
            frame["house_route"] != "no_house"
            for row in logo_gate["rows"]
            for frame in row["sampled_frames"]
        )
        or any(row["logo_supported_frame_count"] for row in logo_gate["rows"])
    ):
        raise ValueError("Origin-view logo coverage changed: review the report")

    html = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light"><title>Curling video project | Supervisor progress briefing</title>
<style>
:root{--ink:#142d38;--navy:#0d2029;--blue:#1c7486;--ice:#e5f3f2;--pale:#f7f6f1;--paper:#fffefb;--muted:#52646b;--line:#d8e1df;--coral:#be584c;--yellow:#e7b950;--good:#2f7c69;--shadow:0 18px 42px rgba(15,36,45,.08)}*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:82px}body{margin:0;background:var(--pale);color:var(--ink);font:16px/1.58 system-ui,-apple-system,"Segoe UI",Arial,sans-serif}a{color:#13687c;text-underline-offset:3px}a:hover{color:#0a4250}button{font:inherit;cursor:pointer}button:focus-visible,a:focus-visible,summary:focus-visible{outline:3px solid var(--yellow);outline-offset:3px}.top{position:sticky;top:0;z-index:20;background:rgba(247,246,241,.96);border-bottom:1px solid var(--line);backdrop-filter:blur(12px)}.top-inner{max-width:1240px;margin:auto;padding:11px 28px;display:flex;align-items:center;gap:18px}.brand{font-size:11px;font-weight:800;letter-spacing:1.7px;text-transform:uppercase;margin-right:auto}.top a{font-size:12px;text-decoration:none;font-weight:650}.top button{background:var(--paper);border:1px solid var(--line);border-radius:7px;padding:7px 10px;font-size:12px}.top button:hover,.top button[aria-pressed=true]{background:var(--navy);color:white}.progress{height:3px;width:0;background:var(--blue)}main{max-width:1240px;margin:auto;padding:0 28px}.hero{display:grid;grid-template-columns:1.3fr .78fr;gap:52px;align-items:center;padding:80px 0 70px}.kicker,.eyebrow{font-size:11px;text-transform:uppercase;letter-spacing:1.8px;font-weight:850;color:var(--blue)}.kicker{display:inline-block;border-left:4px solid var(--coral);padding-left:13px}h1,h2,h3,p{margin-top:0}h1,h2{font-family:Georgia,"Times New Roman",serif;font-weight:400}h1{font-size:clamp(48px,5.8vw,86px);line-height:1.04;letter-spacing:-3.5px;margin:24px 0 23px}h1 em{font-style:normal;color:var(--blue)}h2{font-size:clamp(32px,3.3vw,48px);line-height:1.12;letter-spacing:-1.3px;margin:14px 0 20px;max-width:920px}h3{font-size:19px;line-height:1.3;margin-bottom:9px}.lead{font-size:21px;line-height:1.48;color:#435963;max-width:750px}.meta{font-size:13px;color:var(--muted)}.status{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin:24px 0 0}.tag{display:inline-block;border-radius:40px;background:#f4e2d8;color:#8b3e35;font-size:11px;font-weight:850;letter-spacing:.5px;text-transform:uppercase;padding:6px 11px}.tag.good{background:#deefe7;color:#216452}.tag.blue{background:#dff0f2;color:#186a79}.hero-card{background:var(--navy);color:white;border-radius:16px;padding:34px;box-shadow:var(--shadow);min-height:440px;display:flex;flex-direction:column;justify-content:space-between;overflow:hidden}.hero-card .eyebrow{color:#9ad4d5}.hero-card svg{width:100%;height:auto;max-height:250px}.hero-card strong{font:32px/1.2 Georgia,serif;font-weight:400}.hero-card p{font-size:14px;color:#bad2d6;margin:7px 0 0}.section{border-top:1px solid var(--line);padding:68px 0 72px}.section-head{display:flex;gap:15px;align-items:baseline}.section-head b{font:italic 21px Georgia,serif;color:var(--blue)}.section-intro{font-size:18px;max-width:920px;color:var(--muted)}.grid{display:grid;gap:18px}.grid.three{grid-template-columns:repeat(3,1fr)}.grid.two{grid-template-columns:repeat(2,1fr)}.grid.four{grid-template-columns:repeat(4,1fr)}.card{background:var(--paper);border:1px solid var(--line);border-radius:12px;padding:24px;box-shadow:0 4px 12px rgba(15,36,45,.025)}.card p:last-child{margin-bottom:0}.card.dark{background:var(--navy);color:white;border-color:var(--navy)}.card.dark p{color:#c5dadd}.stat{display:block;font:44px/1 Georgia,serif;letter-spacing:-1.6px;margin:10px 0 11px}.stat small{font:16px system-ui,sans-serif;letter-spacing:0}.sub{font-size:13px;color:var(--muted)}.dark .sub{color:#b8d1d5}.intro-strip{display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px;margin-bottom:28px}.intro-strip .card{border-top:4px solid var(--blue)}.intro-strip .card:nth-child(2){border-top-color:var(--yellow)}.intro-strip .card:nth-child(3){border-top-color:var(--coral)}.architecture{display:grid;grid-template-columns:repeat(6,1fr);gap:10px;margin:26px 0}.stage{background:var(--paper);border:1px solid var(--line);padding:18px 14px;border-radius:10px;min-height:172px;position:relative}.stage:after{content:'→';position:absolute;right:-17px;top:60px;color:var(--blue);z-index:1;font-size:24px}.stage:last-child:after{content:''}.stage strong{display:block;font-size:14px;line-height:1.28;margin:13px 0 8px}.stage p{font-size:12px;color:var(--muted);margin:0}.stage .num{font-size:11px;font-weight:850;color:var(--blue)}.stage.future{border-style:dashed;background:#f4f5ee}.stage.future .num{color:#9c6f2d}.notice{background:#e8f0ed;border-left:4px solid var(--blue);padding:18px 22px;margin:25px 0;border-radius:0 7px 7px 0}.notice.alert{background:#f7ece5;border-color:var(--coral)}.notice p:last-child{margin-bottom:0}.table-wrap{overflow:auto;background:var(--paper);border:1px solid var(--line);border-radius:12px}table{width:100%;border-collapse:collapse;min-width:780px}th,td{padding:17px 18px;text-align:left;vertical-align:top;border-bottom:1px solid var(--line)}tr:last-child td{border-bottom:0}th{font-size:11px;letter-spacing:1.2px;text-transform:uppercase;color:var(--muted);background:#eff3f0}td small{display:block;font-size:12px;color:var(--muted);margin-top:4px}td b{font-weight:750}.figure{background:var(--paper);border:1px solid var(--line);border-radius:12px;padding:16px;overflow:hidden}.figure img{display:block;width:100%;height:auto;border-radius:7px}.figure figcaption{font-size:12px;color:var(--muted);padding:12px 4px 0}.figure.full{margin:24px 0}.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:23px 0}.metric{background:var(--paper);border:1px solid var(--line);border-radius:10px;padding:18px}.metric b{display:block;font:34px Georgia,serif}.metric span{font-size:12px;color:var(--muted)}.bar-label{display:grid;grid-template-columns:155px 1fr 55px;gap:12px;align-items:center;margin:13px 0;font-size:13px}.bar-track{background:#e5ebea;border-radius:99px;overflow:hidden;height:16px}.bar{height:100%;background:var(--blue);border-radius:99px}.bar.coral{background:var(--coral)}.bar.yellow{background:var(--yellow)}.checklist{list-style:none;padding:0;margin:12px 0}.checklist li{padding:9px 0 9px 30px;border-bottom:1px solid var(--line);position:relative}.checklist li:before{content:'✓';position:absolute;left:4px;color:var(--good);font-weight:900}.checklist li.open:before{content:'○';color:var(--coral)}.roadmap{counter-reset:step;display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-top:25px}.roadmap article{background:var(--paper);border:1px solid var(--line);padding:23px;border-radius:10px}.roadmap article:before{counter-increment:step;content:'0' counter(step);display:block;color:var(--blue);font:25px Georgia,serif;margin-bottom:12px}.roadmap p{font-size:14px;color:var(--muted)}.demo-links{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}.demo-links a{text-decoration:none;display:block;color:var(--ink);background:var(--paper);border:1px solid var(--line);padding:22px;border-radius:10px}.demo-links a:hover{border-color:var(--blue);box-shadow:var(--shadow)}.demo-links strong{display:block;margin:10px 0 5px}.demo-links span{font-size:13px;color:var(--muted)}.speaker-notes{display:none;background:#edf5f1;border:1px dashed #8dbcb3;padding:18px 22px;margin:20px 0;font-size:14px;border-radius:8px}.speaker-notes:before{content:'SPEAKER NOTE';display:block;font-size:10px;font-weight:850;letter-spacing:1.5px;color:var(--blue);margin-bottom:8px}body.notes-on .speaker-notes{display:block}body.focus{font-size:19px}body.focus .section-intro{font-size:22px}details{border-bottom:1px solid var(--line);padding:16px 0}summary{cursor:pointer;font-weight:700}details p{margin:10px 0 0;color:var(--muted)}footer{border-top:1px solid var(--line);padding:32px 0 70px;color:var(--muted);font-size:12px}.footlinks{display:flex;gap:17px;flex-wrap:wrap;margin:12px 0}.footlinks a{font-size:12px}@media(max-width:1050px){.architecture{grid-template-columns:repeat(3,1fr)}.stage:nth-child(3):after{content:''}.grid.four,.roadmap{grid-template-columns:repeat(2,1fr)}}@media(max-width:760px){.top a{display:none}.hero{grid-template-columns:1fr;padding:42px 0}.hero-card{min-height:300px}.intro-strip,.grid.three,.grid.two,.demo-links{grid-template-columns:1fr}.metrics{grid-template-columns:repeat(2,1fr)}.architecture{grid-template-columns:repeat(2,1fr)}.stage:nth-child(2):after,.stage:nth-child(4):after{content:''}.stage:nth-child(3):after{content:'→'}main{padding:0 18px}.section{padding:46px 0}h1{letter-spacing:-2px}}@media(max-width:480px){.architecture,.metrics,.roadmap{grid-template-columns:1fr}.stage:after{content:''!important}.top-inner{padding:10px 15px;gap:7px}.brand{font-size:9px}.top button{font-size:10px;padding:6px}.hero-card{display:none}}@media print{body{background:white;font-size:10pt}html{scroll-behavior:auto}.top,.demo-links{display:none}main{max-width:none;padding:0}.hero{padding:0 0 20px;grid-template-columns:1.2fr .8fr;gap:15px}.hero-card{min-height:280px;padding:18px;print-color-adjust:exact}h1{font-size:40pt}h2{font-size:24pt}.lead{font-size:14pt}.section{padding:20px 0;break-before:page}.card,.metric,.figure,.stage,.roadmap article{break-inside:avoid}.speaker-notes{display:none!important}.grid.three,.roadmap{grid-template-columns:repeat(2,1fr)}.architecture{grid-template-columns:repeat(3,1fr)}.tag,.bar,.hero-card{print-color-adjust:exact}table{min-width:0}th,td{padding:8px;font-size:9pt}a{color:var(--ink)}}
</style></head><body>
<header class="top"><div class="top-inner"><span class="brand">CURLING VIDEO / PROJECT UPDATE</span><a href="#results">Evidence</a><a href="#latest">Latest transfer</a><a href="#roadmap">Next steps</a><button id="notes" aria-pressed="false">Speaker notes</button><button id="focus" aria-pressed="false">Large type</button><button id="print">Print / PDF</button></div><div class="progress" id="progress"></div></header>
<main>
<section class="hero" id="start"><div><span class="kicker">Supervisor + team meeting · 9 October 2026 · 10:00</span><h1>From curling video<br>to <em>grounded game events.</em></h1><p class="lead">We can extract provisional throws, link evidence across views, and recover selected board states. The remaining challenge is making those results reliable across full recordings and camera layouts.</p><div class="status"><span class="tag">Research prototype</span><span class="tag good">Reproducible evidence pipeline</span><span class="tag blue">Independent full-match F1 pending</span></div><p class="meta" style="margin-top:22px">Presentation length: about 8 minutes · All evidence and images are embedded for offline viewing; demo links use the project folder.</p><div class="speaker-notes">Open with the useful outcome: we have a real pipeline and viewable artifacts. Then state the limit early: strong partial-window results do not yet prove a robust full-match throw detector.</div></div><div class="hero-card"><span class="eyebrow">Our target system</span><svg viewBox="0 0 470 240" aria-hidden="true"><rect x="34" y="25" width="402" height="190" rx="95" fill="#e9f5f4"/><path d="M102 25v190M368 25v190" stroke="#a9cfd0" stroke-width="3" stroke-dasharray="6 7"/><circle cx="367" cy="120" r="73" fill="#acd0d6"/><circle cx="367" cy="120" r="52" fill="#e9f5f4"/><circle cx="367" cy="120" r="30" fill="#cf8176"/><circle cx="367" cy="120" r="14" fill="#e9f5f4"/><path d="M104 115 C172 114 237 111 302 119" fill="none" stroke="#137f88" stroke-width="5" stroke-linecap="round" stroke-dasharray="1 11"/><circle cx="106" cy="115" r="16" fill="#e7b950" stroke="#0d2029" stroke-width="5"/><circle cx="303" cy="119" r="14" fill="#e7b950" stroke="#0d2029" stroke-width="5"/><circle cx="380" cy="130" r="12" fill="#bd594b" stroke="#0d2029" stroke-width="4"/><path d="M65 120h23M320 120h24" stroke="#6b9da6" stroke-width="2"/></svg><div><strong>Video → throw → board → coaching</strong><p>Each arrow needs an observable source, uncertainty, and a test.</p></div></div></section>

<section class="section" id="snapshot"><div class="section-head"><b>01</b><span class="eyebrow">Executive snapshot</span></div><h2>Built enough to demonstrate; not enough to claim automation at scale.</h2><div class="intro-strip"><article class="card"><span class="eyebrow">What works</span><h3>Evidence-rich throw candidates</h3><p>Video, colour motion, camera cuts and delayed scoreboard changes flow into an ordered ledger with links back to the source.</p></article><article class="card"><span class="eyebrow">Best partial transfer</span><h3>0.95 timing F1</h3><p>Canada–USA 2024: 19 correct, one extra, one missed coarse window over 18.5 minutes. This is a same-production, agent-authored reference.</p></article><article class="card"><span class="eyebrow">Main gap</span><h3>Full-match reliability</h3><p>The new Canada–Norway 2022 transfer produces excess candidates and colour conflicts. No independent complete-recording precision/recall exists yet.</p></article></div><div class="notice"><strong>The honest status:</strong> a source-specific research prototype with useful event and board evidence. The 0.95 precision and 0.95 recall acceptance gate on complete, independently referenced recordings has <strong>not been met</strong>.</div><div class="speaker-notes">Avoid calling the 0.95 result overall accuracy. It measures timing agreement on a short same-family interval against coarse windows prepared by the developing agent.</div></section>

<section class="section" id="built"><div class="section-head"><b>02</b><span class="eyebrow">What exists today</span></div><h2>One pipeline, with explicit uncertainty at each stage.</h2><div class="architecture"><div class="stage"><span class="num">01 · BUILT</span><strong>Ingest + view routing</strong><p>Reads full videos, detects cuts and routes known layouts. Unknown spans remain gaps.</p></div><div class="stage"><span class="num">02 · BUILT</span><strong>Stone evidence</strong><p>Colour caps, learned boxes, local tracks and image-to-ice calibration.</p></div><div class="stage"><span class="num">03 · BUILT</span><strong>Throw candidates</strong><p>Early-view passages, cross-view motion and counter-linked event windows.</p></div><div class="stage"><span class="num">04 · PARTIAL</span><strong>Game-state observations</strong><p>Stable partial boards from selected overhead frames, compared with official diagrams.</p></div><div class="stage future"><span class="num">05 · NEXT</span><strong>Validated trajectories</strong><p>Physical stone identity, exact phase boundaries and calibrated continuous paths.</p></div><div class="stage future"><span class="num">06 · FUTURE</span><strong>Coaching agent</strong><p>Simulation and grounded feedback only after events and states are reliable.</p></div></div><div class="grid two"><figure class="figure"><img src="__CROSS_IMAGE__" alt="Four real source frames show a yellow stone in departure and receiving camera views, with observed image points below."><figcaption>Existing cross-view prototype: one yellow stone shown before and after the broadcast camera handoff. This is a proposed link, not independently proven identity.</figcaption></figure><div class="card"><span class="eyebrow">Working artifacts</span><ul class="checklist"><li>One-end demo with 16 detected passages and 16 provisional two-view links.</li><li>Full-source event ledger with candidate windows, colour status, counter links and explicit gaps.</li><li>Source-linked official shot and board references for evaluation.</li><li>Interactive cross-view, segment and board evidence viewers.</li><li class="open">Complete throw boundaries and continuous physical trajectories.</li><li class="open">Validated game states, simulations and grounded coaching.</li></ul></div></div><div class="speaker-notes">Use the cross-view image as a 30-second demo. Point out the broadcast cut: we cannot claim we saw the stone continuously through that gap.</div></section>

<section class="section" id="results"><div class="section-head"><b>03</b><span class="eyebrow">Measured evidence</span></div><h2>Promising intervals, visible transfer failures.</h2><p class="section-intro">The table keeps scoring method and scope beside each number. It is deliberately not a leaderboard of interchangeable F1 scores.</p><div class="table-wrap"><table><thead><tr><th>Experiment</th><th>Result</th><th>What it establishes</th><th>Limit</th></tr></thead><tbody>
<tr><td><b>Stone localisation</b><small>Selected development frames</small></td><td><b>40/48</b> within 10 cm</td><td>Calibrated body localisation is feasible on chosen views.</td><td>Manual calibration and diagram references; not an unseen-video rate. <a href="prototype/body-localization/index.html">Evidence</a></td></tr>
<tr><td><b>Canada–USA 2024</b><small>18.5-minute frozen transfer</small></td><td><b>19 TP / 1 FP / 1 FN</b><small>Timing F1 0.950</small></td><td>Early-view span detector transfers within one production family.</td><td>Coarse agent-authored windows; not a full match. <a href="validation/throw-event-benchmark/canada-usa-2024/RESULTS.md">Result</a></td></tr>
<tr><td><b>Canada–Estonia 2024</b><small>Earlier frozen transfer</small></td><td><b>13 / 0 / 4</b><small>Timing F1 0.867</small></td><td>Fixed pixel-speed and virtual-line rules lose real throws.</td><td>Partial interval; same-family coarse reference. <a href="validation/throw-event-benchmark/canada-estonia-2024/RESULTS.md">Result</a></td></tr>
<tr><td><b>Canada–Norway 2022</b><small>New full-match transfer</small></td><td><b>142 candidates</b><small>128 official shots</small></td><td>Counter linkage reaches 100 readable updates, but the ledger has excess candidates.</td><td>No official video release times; no full-match event F1. <a href="validation/throw-event-benchmark/paralympics-2022-canada-norway/RESULTS.md">Result</a></td></tr>
<tr><td><b>Adjacent-view pairing</b><small>Norway end 3 → end 4</small></td><td><b>End 4: 10/12</b><small>Only 6 colour-concordant</small></td><td>Pairing departure and receiving views cuts duplicate cues, but still selects the wrong stone or misses updates.</td><td>Delayed counter proxy covers 12/16 throws; same-match development, not physical event F1. <a href="validation/curlobserver-learned-probe/cap-patch-crossmatch-v1/NORWAY-ORIGIN-RECEIVER.md">Study</a></td></tr>
<tr><td><b>Mirrored early line</b><small>Norway end 4 → end 6</small></td><td><b>19 partition cues</b><small>10/12 counter colours</small></td><td>A motion-routed left/right line handles changing delivery direction, but held stones and early cuts remain unresolved.</td><td>Fixed line failed on end 5; delayed counter proxy, not physical event F1. <a href="validation/curlobserver-learned-probe/cap-patch-crossmatch-v1/MIRRORED-GATE.md">Study</a></td></tr>
<tr><td><b>Public stone-box clips</b><small>20 held-out clips, 985 labelled frames</small></td><td><b>F1 0.681 → 0.859</b><small>18/20 clips improved</small></td><td>Retraining the stone patch model reduces false boxes while retaining most true stones.</td><td>Broadcast side-view check is mixed; model not adopted. Clip split may share source material; no throw-event score. <a href="validation/curlobserver-learned-probe/public-tracking-v2/README.md">Result</a> · <a href="https://github.com/CurlObserver/dataset">Dataset</a></td></tr>
<tr><td><b>Temporal boards</b><small>15 selected, counter-anchored shots</small></td><td><b>7 partial boards</b><small>22/22 emitted stones match; 5 complete</small></td><td>Video can support stable 2D board observations on selected overhead views.</td><td>Eight shots emit no board; selected development sample. <a href="validation/official-shot-sequence/PWG2022-BOARD-STATE.md">Result</a></td></tr>
</tbody></table></div><p class="sub" style="margin-top:12px">TP = matched throw; FP = extra candidate; FN = missed throw. F1 combines precision and recall. Scores from different reference types are not directly comparable.</p><div class="speaker-notes">The strongest event transfer is Canada–USA 2024, but the hard evidence against generalisation is just as important: Estonia missed four throws, and 2022 video needs a different route entirely. Adjacent-view pairing failed colour transfer to end four. The virtual line failed when the delivery view flipped and still misses some held stones even after routing. The 0.859 number is stone-box F1 on public clips, not event F1.</div></section>

<section class="section" id="latest"><div class="section-head"><b>04</b><span class="eyebrow">Latest full-match case study</span></div><h2>Canada–Norway 2022 shows the current bottleneck.</h2><p class="section-intro">We froze the models and rules before processing a new match, then compared against the official 128-shot order and delayed broadcast counters. An <em>end</em> is a round; this match has eight ends of 16 deliveries. The on-screen counter shows stones remaining and often updates after the delivery. The official book contains no video release timestamps.</p><div class="metrics"><div class="metric"><b>128</b><span>Official numbered shots</span></div><div class="metric"><b>142</b><span>Provisional video candidates</span></div><div class="metric"><b>100</b><span>Readable counter changes linked</span></div><div class="metric"><b>42</b><span>Candidates without counter link</span></div></div><div class="grid two"><div><h3>The complete counter-anchored end</h3><p>End 2 has 16 clean counter anchors. The cap-motion detector proposed 16 visual events; 15 matched delayed counter timing. Yet only nine matches have the correct known colour: four conflict and two have unknown visual colour. One official shot and one candidate remain unmatched.</p><div class="bar-label"><span>Timing pairs</span><div class="bar-track"><div class="bar" style="width:93.75%"></div></div><b>15/16</b></div><div class="bar-label"><span>Known colour match</span><div class="bar-track"><div class="bar yellow" style="width:56.25%"></div></div><b>9/16</b></div><div class="bar-label"><span>Colour conflicts</span><div class="bar-track"><div class="bar coral" style="width:25%"></div></div><b>4/16</b></div><p class="sub">These are delayed-counter proxy comparisons, not independent physical throw precision or recall. The frozen held-cap rescue added 0 events across 32 eligible windows.</p></div><figure class="figure"><img src="__CONFLICT_IMAGE__" alt="Canada–Norway second-end broadcast frame with a yellow delivery stone in the lower central ice and red-clothed people elsewhere."><figcaption>Post-score source frame at 23:12. A yellow delivery stone is visible. The colour-motion rule can still find red tracks elsewhere; temporal pairing and object identity both need improvement.</figcaption></figure></div><div class="notice alert"><strong>Current experiment:</strong> a simple lower-ice spatial gate retained sustained motion in only 52 of 114 cap-confirmed windows on this now-exposed match. It cannot be promoted as a hard veto without losing coverage. We need continuous stone identity and view-aware evidence, not another blunt threshold.</div><div class="speaker-notes">The number 142 is not an F1 score. It means the provisional list exceeds the official count by 14, so it cannot already be one clean event per official shot. Counter linkage is delayed and can pair with the wrong episode.</div></section>

<section class="section" id="state"><div class="section-head"><b>05</b><span class="eyebrow">From events to game state</span></div><h2>We have reference states and partial video states. The gap is explicit.</h2><div class="grid three"><article class="card"><span class="eyebrow">Reference library</span><span class="stat">477</span><p>Official numbered shot diagrams across four Beijing 2022 matches: 349 in the original three-game set plus 128 Canada–Norway snapshots. These are reference observations, not video reconstructions.</p></article><article class="card"><span class="eyebrow">Video-derived probe</span><span class="stat">7 <small>partial boards</small></span><p>Temporal consensus emitted 22 stone positions; all matched official diagrams within the study tolerance. Five boards were complete, eight of 15 sampled shots produced no board.</p></article><article class="card dark"><span class="eyebrow">Simulation readiness</span><span class="stat">Not yet</span><p>Physical coordinates, persistent stone identities, reliable settle times and trajectories are still missing. A 3D replay or coaching agent would otherwise invent facts.</p></article></div><div class="notice"><strong>Data handoff now built:</strong> seven video-derived partial boards and 22 stone observations are exported with source hashes, time spans and unitless house coordinates. Every snapshot remains marked incomplete/unknown and not simulation-ready. Only validated states should enter a simulator. <a href="validation/official-shot-sequence/pwg2022-video-partial-board-observations.json">Inspect the export</a>.</div><div class="speaker-notes">The official PDF boards let us check future reconstruction; feeding those PDF positions directly into a simulation would bypass the video task. The video-derived results are promising but selected and incomplete.</div></section>

<section class="section" id="roadmap"><div class="section-head"><b>06</b><span class="eyebrow">Concrete next milestones</span></div><h2>Raise reliability before adding interpretation.</h2><div class="roadmap"><article><h3>Track the stone, not just its colour</h3><p>Recognise the held stone and its motion onset before a cut, route the active delivery side, reject players/graphics, and preserve uncertainty across views.</p></article><article><h3>Resolve event sequence</h3><p>Use one-to-one shot assignment, end context and counters as delayed evidence; keep conflicts and missing-view throws explicit.</p></article><article><h3>Prove the detector</h3><p>Freeze on development videos, then score complete untouched recordings from both production families against exhaustive independent labels.</p></article><article><h3>Build grounded state + replay</h3><p>Stitch stable boards, calibrate to ice coordinates, retain trajectory gaps, then test 2D/3D simulation and coaching summaries.</p></article></div><div class="grid two" style="margin-top:18px"><div class="card"><span class="eyebrow">Acceptance gate</span><h3>Precision ≥ 0.95 and recall ≥ 0.95</h3><p>For each complete held-out recording, with zero post-hoc timing tolerance, explicit colour errors, quiet periods and full coverage. F1 is reported too, but cannot hide weak precision or recall.</p></div><div class="card"><span class="eyebrow">What the team can decide tomorrow</span><h3>Prioritise the target use case</h3><p>Which broadcast format and coaching question matter most? Which sources can supply independent event and settled-board references? This fixes the evaluation target before more model tuning.</p></div></div><div class="speaker-notes">Propose the next sprint as held-stone recognition, event identity and independent evaluation, then state reconstruction. Simulation is a destination, not a substitute for measured states.</div></section>

<section class="section" id="demo"><div class="section-head"><b>07</b><span class="eyebrow">Show, then discuss</span></div><h2>A practical 8-minute meeting path.</h2><div class="grid two"><div class="card"><ol><li><strong>1 minute:</strong> state the target and current prototype status.</li><li><strong>2 minutes:</strong> open the cross-view and throw-segment demos.</li><li><strong>2 minutes:</strong> show the measured transfer table and Canada–Norway failure.</li><li><strong>1 minute:</strong> show partial board-state evidence.</li><li><strong>2 minutes:</strong> agree on the next evaluation target and team responsibilities.</li></ol></div><div class="card"><h3>Two sentences to use</h3><p>“We can already turn selected curling video into source-linked throw candidates and partial board observations. The main research problem is proving that each candidate is the delivered stone across camera changes, with high precision and recall over a complete match.”</p><p>“Our newest full-match test exposes the gap: 142 provisional candidates for 128 official throws, and colour conflicts even when event timing matches the scoreboard.”</p></div></div><div class="demo-links" style="margin-top:18px"><a href="prototype/cross-view/index.html"><span class="eyebrow">Demo 1</span><strong>Cross-view stone evidence ↗</strong><span>One-end two-camera viewer; inspect T11 and other proposed links.</span></a><a href="prototype/throw-segments/index.html"><span class="eyebrow">Demo 2</span><strong>Throw segments ↗</strong><span>Sixteen passage-to-passage review windows with partial trajectories.</span></a><a href="validation/official-shot-sequence/PWG2022-BOARD-STATE.md"><span class="eyebrow">Evidence 3</span><strong>Board-state audit ↗</strong><span>Official diagrams and the video-derived partial board experiment.</span></a></div><p class="sub" style="margin-top:18px">The report itself works offline. Local demo links require this HTML file to remain in the project root with its companion data and videos; external official-source links require internet.</p></section>

<section class="section" id="sources"><div class="section-head"><b>08</b><span class="eyebrow">Evidence and qualifications</span></div><h2>Sources a reviewer can inspect.</h2><details><summary>Event evaluation protocol</summary><p><a href="validation/throw-event-benchmark/README.md">Acceptance gate and score definitions</a> · <a href="validation/throw-event-benchmark/canada-usa-2024/RESULTS.html">Canada–USA frozen result</a> · <a href="validation/throw-event-benchmark/canada-estonia-2024/RESULTS.md">Canada–Estonia frozen failure</a>.</p></details><details><summary>Canada–Norway 2022 provenance</summary><p><a href="validation/throw-event-benchmark/paralympics-2022-canada-norway/TRANSFER-PLAN.md">Pre-run transfer plan and hashes</a> · <a href="validation/throw-event-benchmark/paralympics-2022-canada-norway/FIRST-TRANSFER.json">First-run machine-readable audit</a> · <a href="validation/throw-event-benchmark/paralympics-2022-canada-norway/RESULTS.md">Interpretation</a> · <a href="https://www.youtube.com/watch?v=EoSwgOcH71g">Official replay</a> · <a href="https://curlit.com/PDF/PWG2022_ResultsBook.pdf">Official results book</a>.</p></details><details><summary>Game-state and geometry evidence</summary><p><a href="validation/official-shot-sequence/PWG2022-BOARD-STATE.md">Board reference and transfer audits</a> · <a href="prototype/body-localization/index.html">Stone-localisation report</a> · <a href="prototype/cross-view/index.html">Cross-view viewer</a>.</p></details><details><summary>What is not independently proven</summary><p>No exhaustive independent full-match throw timestamps, no validated release instants, no robust persistent identity across all camera cuts, no full video-derived board sequence, no physically verified trajectory, and no simulation or coaching accuracy. The reserved Wetzikon source remains outside development.</p></details></section>
<footer><strong>Prepared for the 9 October 2026 supervisor and team meeting.</strong><div class="footlinks"><a href="README.md">Project README</a><a href="validation/throw-event-benchmark/README.md">Evaluation protocol</a><a href="validation/throw-event-benchmark/paralympics-2022-canada-norway/RESULTS.md">Latest transfer</a></div><p>Speaker notes: press N · Large type: press L · Print / PDF: use the top button or Ctrl/Cmd+P.</p></footer>
</main><script>
function toggle(name,id){var active=document.body.classList.toggle(name);document.getElementById(id).setAttribute('aria-pressed',String(active))}document.getElementById('notes').onclick=function(){toggle('notes-on','notes')};document.getElementById('focus').onclick=function(){toggle('focus','focus')};document.getElementById('print').onclick=function(){window.print()};document.addEventListener('keydown',function(event){if(event.altKey||event.ctrlKey||event.metaKey||/INPUT|TEXTAREA|SELECT/.test(event.target.tagName))return;if(event.key.toLowerCase()==='n')document.getElementById('notes').click();if(event.key.toLowerCase()==='l')document.getElementById('focus').click()});function updateProgress(){var root=document.documentElement;document.getElementById('progress').style.width=(100*root.scrollTop/(root.scrollHeight-root.clientHeight||1))+'%'}window.addEventListener('scroll',updateProgress,{passive:true});updateProgress();
</script></body></html>"""
    html = html.replace(
        "</style>",
        ".meeting-guide{padding-top:46px}.brief-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:25px 0}"
        ".brief-grid article{background:var(--paper);border:1px solid var(--line);border-radius:11px;padding:20px}"
        ".brief-grid article:nth-child(3){border-top:4px solid var(--coral)}"
        ".brief-grid h3{margin:10px 0}.brief-grid p{font-size:13px;color:var(--muted);margin:0}"
        ".brief-speech{background:var(--navy);color:white;border-radius:12px;padding:26px 30px;margin:24px 0}"
        ".brief-speech .eyebrow{color:#9ad4d5}.brief-speech p{font:23px/1.5 Georgia,serif;margin:10px 0 0}"
        ".strategy-card{background:#eef6f4;border:1px solid #9dc5bf;border-left:5px solid var(--good);border-radius:12px;padding:22px 25px;margin:22px 0}"
        ".strategy-card h3{font:29px/1.2 Georgia,serif;margin:7px 0 16px}.strategy-steps{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}"
        ".strategy-steps article{background:white;border:1px solid var(--line);border-radius:8px;padding:14px}.strategy-steps b{color:var(--ink)}"
        ".strategy-steps p{font-size:13px;line-height:1.45;margin:7px 0 0}.strategy-card .strategy-evidence{margin:16px 0 8px;font-size:15px}"
        ".strategy-card .strategy-limit{font-size:13px;color:var(--muted);margin:0}"
        "@media(max-width:900px){.brief-grid{grid-template-columns:repeat(2,1fr)}}"
        "@media(max-width:700px){.strategy-steps{grid-template-columns:1fr}}"
        "@media(max-width:550px){.brief-grid{grid-template-columns:1fr}.brief-speech p{font-size:19px}}"
        "@media print{.brief-grid{grid-template-columns:repeat(2,1fr)}.brief-speech{print-color-adjust:exact}}"
        "</style>",
        1,
    )
    html = html.replace(
        '<a href="#results">Evidence</a>', '<a href="#briefing">Meeting guide</a>', 1
    )
    html = html.replace(
        '<section class="section" id="snapshot">',
        '<section class="section meeting-guide" id="briefing"><div class="section-head"><b>00</b>'
        '<span class="eyebrow">Meeting guide</span></div>'
        "<h2>The four points to report.</h2>"
        '<p class="section-intro">If time is short, use this page. The technical sections below support each claim.</p>'
        '<div class="brief-grid">'
        '<article><span class="eyebrow">1 · Goal</span><h3>Detect every delivered stone</h3>'
        "<p>Segment a whole broadcast into throw events, then reconstruct observed paths and stone positions. High precision and recall on complete, independently labelled videos are the target.</p></article>"
        '<article><span class="eyebrow">2 · Demonstration</span><h3>One end already works</h3>'
        "<p>On the Canada–Korea development end, 16 of 16 internally prepared passage windows match. T11 shows 31 departure and 29 receiving positions after a targeted range extension. Both views contain a candidate at 46.7 s, but their nominal longitudinal positions differ by 0.61 m.</p></article>"
        '<article><span class="eyebrow">3 · Transfer</span><h3>Generalisation is the problem</h3>'
        "<p>Canada–USA reaches 19 matched passages, one extra and one missed coarse window on 18.5 minutes. Estonia misses four. A 2022 full-match run produces 142 candidates for 128 official shots. These scores do not prove full-match event F1.</p></article>"
        '<article><span class="eyebrow">4 · Decision</span><h3>Choose the next validation</h3>'
        "<p>Agree on the target broadcast family and an exhaustive independent reference for whole matches. Then prioritise camera-aware stone identity and test precision and recall before simulation or coaching.</p></article>"
        '</div><div class="strategy-card" id="recall-filter"><span class="eyebrow">Detection strategy</span>'
        '<h3>Keep plausible throws, then filter false alarms.</h3><div class="strategy-steps">'
        "<article><b>1 · Recall-oriented proposals</b><p>Collect plausible moving-stone passages across camera layouts. Keep the raw candidates, including ones that may later be rejected.</p></article>"
        "<article><b>2 · Visual-context filter</b><p>Confirm candidates using image context and motion. Reject lookalikes without discarding the underlying evidence.</p></article>"
        "<article><b>3 · Auditable decisions</b><p>Save confirmed and withheld candidates in a review ledger. Score both missed throws and extra events on complete videos.</p></article>"
        '</div><p class="strategy-evidence"><strong>Development evidence (TP/FP/FN):</strong> USA 19/20/1 raw → 19/1/1 filtered; Estonia 16/5/1 → 16/0/1; China 17/9/1 → 17/1/1. The filter cuts false alarms while retaining the raw matches on these excerpts.</p>'
        '<p class="strategy-limit">Each raw pool still misses one labelled passage. A filter cannot recover a throw absent from its proposal pool. These are exposed partial intervals with agent-made references, not independent full-match scores. <a href="validation/two-stage-throw-audit/index.html">Inspect the two-stage audit ↗</a></p></div>'
        '<div class="brief-speech"><span class="eyebrow">Say this in about one minute</span>'
        "<p>“Our direction is a high-recall proposal stage followed by a visual-context filter. On three development excerpts, the filter removes many false alarms while retaining the raw matches; each raw pool still misses one labelled passage. T11 also shows candidate trajectories in both cameras, with a 0.61-metre geometric disagreement at the handoff. Next we must improve proposal coverage and validate the full pipeline on independently labelled complete matches.”</p></div>"
        '<div class="notice alert"><strong>Keep the claim precise:</strong> 16/16 is one development end; 0.950 F1 is a short same-family timing check against agent-prepared windows; 142 versus 128 is an excess-candidate count, not a full-match F1. Exact release and continuous physical trajectory are not validated.</div>'
        '<div class="demo-links"><a href="prototype/trajectory-accuracy/index.html"><span class="eyebrow">Show the demonstration</span><strong>T11 in two cameras ↗</strong></a>'
        '<a href="validation/throw-event-benchmark/canada-usa-2024/RESULTS.html"><span class="eyebrow">Show the measured score</span><strong>Canada–USA 19/1/1 ↗</strong></a>'
        '<a href="#latest"><span class="eyebrow">Show the failure</span><strong>Canada–Norway 2022 ↗</strong></a></div>'
        '</section>\n<section class="section" id="snapshot">',
        1,
    )
    html = html.replace(
        '<section class="section" id="built">',
        '<section class="section" id="korea"><div class="section-head"><b>→</b>'
        '<span class="eyebrow">One recording through the pipeline</span></div>'
        "<h2>Canada–Korea 2024: detect a passage, then inspect its arrival.</h2>"
        '<p class="section-intro">For the meeting, follow one 18.5-minute end-three '
        "video from a virtual-line stone-passage detector to a partial "
        "receiving-view trajectory. This is the strongest coherent demonstration "
        "of the intended workflow, with its uncertainty shown beside each output.</p>"
        '<div class="grid three">'
        '<article class="card"><span class="eyebrow">Event detection</span>'
        '<span class="stat">16/16</span><p>All 16 coarse, internally prepared '
        "passage windows matched one-to-one, with no extra candidate in this "
        "same end. The virtual line marks stone passage, not physical release.</p></article>"
        '<article class="card"><span class="eyebrow">One arrival</span>'
        '<span class="stat">T11</span><p>The yellow stone has an observed '
        "receiving-camera path and a provisional settled point. The link across "
        "the camera cut uses colour, timing and motion; physical identity is "
        "not verified.</p></article>"
        '<article class="card"><span class="eyebrow">Trajectory check</span>'
        '<span class="stat">1.16 <small>px</small></span><p>Retrospective RMSE '
        "on four manually read moving points. Both sides share calibration; "
        "this does not measure centimetre accuracy on the ice.</p></article>"
        '</div><figure class="figure full"><img src="__T11_JOINED__" '
        'alt="T11: departure and receiving camera trajectories overlap in time but differ by 0.61 metres at the same frame.">'
        "<figcaption>T11 has 31 departure positions and 29 receiving positions, including 15 provisional far-range points. "
        "Both cameras show a candidate at 46.7 s, with a 0.61 m nominal longitudinal and 0.09 m lateral disagreement. The cross-camera identity and physical "
        'coordinates remain provisional. <a href="prototype/cross-view/index.html">Open the interactive two-camera trajectory ↗</a></figcaption></figure>'
        '<div class="notice"><strong>Release timing:</strong> The frozen moving-stone tracks begin 0.3–1.5 seconds before their virtual-line crossings (median 0.7 seconds). For T11, source-frame review first shows a clearly separable moving stone at 2303.433 s, the frozen track starts at 2303.500 s, and the line is crossed at 2303.956 s. Separation from the delivery device is hidden by the player and remains unknown. <a href="prototype/throw-analysis/observed-onset-v1.json">Inspect all 16 onsets</a>.</div>'
        '<figure class="figure full"><img src="__T11_RELEASE__" alt="T11 source frames before and after the moving yellow stone becomes visible, while the player hides physical release.">'
        "<figcaption>Selected retrospective source-frame audit: first visible motion is a better review anchor than the later line crossing, but it is not the physical release time.</figcaption></figure>"
        '<div class="notice alert"><strong>Scope:</strong> This is one '
        "development end and one selected arrival trajectory. The eight later "
        "passages were checked after the detector was frozen, but still share "
        "the recording and internally prepared reference. The middle of the "
        "throw, cross-view identity, complete board and physical accuracy "
        "remain unverified.</div>"
        '<div class="demo-links">'
        '<a href="prototype/throw-analysis/index.html"><span class="eyebrow">Start here</span>'
        "<strong>Sixteen passage detections ↗</strong><span>Inspect T11 in the "
        "continuous end-three video.</span></a>"
        '<a href="prototype/trajectory-accuracy/index.html"><span class="eyebrow">Follow the stone</span>'
        "<strong>T11 arrival trajectory ↗</strong><span>Observed points, "
        "manual readings and honest limits.</span></a>"
        '<a href="prototype/continuous/index.html"><span class="eyebrow">Inspect both cameras</span>'
        "<strong>90-second two-view clip ↗</strong><span>Camera-local stone "
        "tracks and registration status.</span></a></div>"
        '<div class="speaker-notes">Lead with this one recording: the line crossing '
        "is a practical event anchor, T11 demonstrates a partial receiving path, "
        "and the missing cross-camera identity is the research gap. Then use "
        "the transfer table to show why the same result cannot yet be claimed "
        "for arbitrary match video.</div></section>\n"
        '<section class="section" id="built">',
        1,
    )
    html = html.replace(
        "We can extract provisional throws, link evidence across views, and recover selected board states. The remaining challenge is making those results reliable across full recordings and camera layouts.",
        "The Canada–Korea end-three video shows stone passages and one partial arrival trajectory in a single recording. The remaining challenge is making that chain reliable across complete matches and camera layouts.",
        1,
    )
    html = html.replace(
        "<li><strong>2 minutes:</strong> open the cross-view and throw-segment demos.</li>",
        "<li><strong>2 minutes:</strong> show Canada–Korea T11: passage detection, receiving-view trajectory and the camera-cut gap.</li>",
        1,
    )
    html = html.replace(
        "“We can already turn selected curling video into source-linked throw candidates and partial board observations. The main research problem is proving that each candidate is the delivered stone across camera changes, with high precision and recall over a complete match.”",
        "“In one Canada–Korea end, we found all 16 annotated stone passages and can trace one arrival on the receiving camera. The research problem is linking those views to the same physical stone and proving complete-match precision and recall elsewhere.”",
        1,
    )
    html = html.replace(
        "<tr><td><b>Public stone-box clips</b>",
        "<tr><td><b>Held-stone cue</b><small>Norway end 6 development → first end 7 transfer</small></td>"
        "<td><b>End 7: 10/12</b><small>14 candidates; 10/10 paired colours agree</small></td>"
        "<td>Held or moving caps near the delivery player can correct known colour errors, "
        "but the frozen cue made zero overrides and recovered no additional counter-backed "
        "events on end seven.</td><td>End-six correction was postscore; end-seven counter "
        "coverage is 12/16 and same-match. No physical event F1. "
        '<a href="validation/curlobserver-learned-probe/cap-patch-crossmatch-v1/HELD-ORIGIN.md">Study</a></td></tr>\n'
        "<tr><td><b>Public stone-box clips</b>",
    )
    html = html.replace(
        "<tr><td><b>Public stone-box clips</b>",
        "<tr><td><b>Early-line first end-8 transfer</b><small>Norway end 8; tie-break frozen after end 7</small></td>"
        "<td><b>8/9 counter pairs</b><small>16 candidates; 7/8 paired colours agree</small></td>"
        "<td>The motion-routed line switches sides, but a new transit-quality tie-break "
        "makes zero changes and the counter proxy still has one colour conflict.</td>"
        "<td>Only 9/16 official deliveries have clean counters; 8 visual candidates "
        "are unpaired. No physical event F1. "
        '<a href="validation/curlobserver-learned-probe/cap-patch-crossmatch-v1/GATE-TRANSIT-TIEBREAK.md">Study</a></td></tr>\n'
        "<tr><td><b>Public stone-box clips</b>",
    )
    html = html.replace(
        "<tr><td><b>Public stone-box clips</b>",
        "<tr><td><b>Non-origin motion fallback</b><small>Norway end 7 development → two other recordings</small></td>"
        "<td><b>1 / 0 / 4</b><small>End 7 / Slovakia / Switzerland candidates</small></td>"
        "<td>Adjacent same-colour motion can flag a rejected delivery view, but fires "
        "on unrelated activity. A retrospective phase check removes three Swiss "
        "cues. Frozen on full China, it emits two candidates across 630 camera "
        "shots; both already exist in the event ledger.</td>"
        "<td>One China candidate conflicts with its linked counter colour; "
        "no new shot window is recovered. Phase correction was postscore on "
        "Swiss. No independent labels or event F1; not promoted. "
        '<a href="validation/curlobserver-learned-probe/cap-patch-crossmatch-v1/NONORIGIN-PHASE-V2.md">Audit</a></td></tr>\n'
        "<tr><td><b>Public stone-box clips</b>",
    )
    html = html.replace(
        '</tbody></table></div><p class="sub" style="margin-top:12px">TP =',
        "<tr><td><b>Adjacent video boards</b><small>Swiss development → China first transfer</small></td>"
        "<td><b>3/5 → 2/5</b><small>Complete boards: 3 → 0; 2 Swiss local transitions</small></td>"
        "<td>Consecutive boards can be recovered in a favorable Swiss view. China "
        "close-ups retain one stone; later selected wide-view development "
        "recovers body contacts and a provisional three-stone fusion.</td>"
        "<td>Five-shot windows, not general rates. Simple ellipse normalization "
        "places only 1/3 elevated cap centres within tolerance; body-contact "
        "points and the adjacent fused board each reach 3/3 under a 180° view "
        "hypothesis in postscore analysis. Swiss first transfer retains 1/2 "
        "visible stones; a postscore blue-ring fix recovers 2/2. The painted "
        "button emblem independently resolves a 180° view reversal in both "
        "selected China and Swiss handoffs. Five frozen Slovakia windows yield "
        "no stable wide contacts. Existing house detectors found no usable "
        "logo in 57 sampled Norway delivery-view frames, so this has not "
        "improved throw detection. Not simulation-ready. "
        '<a href="validation/official-shot-sequence/CHINA-ADJACENT-BOARD-FIRST-TRANSFER.md">Transfer</a></td></tr>'
        '</tbody></table></div><p class="sub" style="margin-top:12px">TP =',
    )
    html = html.replace(
        "<strong>Current experiment:</strong> a simple lower-ice spatial gate retained sustained motion in only 52 of 114 cap-confirmed windows on this now-exposed match. It cannot be promoted as a hard veto without losing coverage. We need continuous stone identity and view-aware evidence, not another blunt threshold.",
        "<strong>Latest transfer:</strong> the mirrored early line plus frozen held-stone cue "
        "found 14 coloured candidates in Norway end seven, matching 10 of 12 clean "
        "delayed counters. All ten paired colours agreed, but two counter-backed events "
        "were missed and four candidates were unpaired. This is same-match proxy evidence, "
        "not physical event F1. Earlier, a lower-ice spatial gate retained motion in only "
        "52 of 114 cap-confirmed windows; it is too lossy as a hard veto. "
        "On end eight, a frozen transit-quality tie-break made no changes; "
        "the original gate paired 8 of 9 clean counters, with one colour conflict.",
    )
    html = html.replace(
        'Only validated states should enter a simulator. <a href="validation/official-shot-sequence/pwg2022-video-partial-board-observations.json">Inspect the export</a>.',
        "All seven boards now have a source-scoped provisional event candidate with "
        "the same delayed counter update, forming a concrete event-to-state evidence "
        "handoff. This does not establish delivered-stone identity or a state transition. "
        "Only validated states should enter a simulator. "
        '<a href="validation/official-shot-sequence/EVENT-BOARD-HANDOFF.md">Inspect the handoff</a>.',
    )
    html = html.replace(
        '<span class="stat">7 <small>partial boards</small></span><p>Temporal consensus emitted 22 stone positions; all matched official diagrams within the study tolerance. Five boards were complete, eight of 15 sampled shots produced no board.</p>',
        '<span class="stat">9 <small>partial boards</small></span><p>The original 15-shot sample produced seven boards and 22 matched stones. A targeted adjacent-shot scan added two boards and four stones, with two local observed transitions. Coverage remains selective.</p>',
    )
    html = html.replace(
        'seven video-derived partial boards and 22 stone observations are exported with source hashes, time spans and unitless house coordinates. Every snapshot remains marked incomplete/unknown and not simulation-ready. All seven boards now have a source-scoped provisional event candidate with the same delayed counter update, forming a concrete event-to-state evidence handoff. This does not establish delivered-stone identity or a state transition. Only validated states should enter a simulator. <a href="validation/official-shot-sequence/EVENT-BOARD-HANDOFF.md">Inspect the handoff</a>.',
        'nine video-derived partial boards and 26 stone observations are exported with source hashes, time spans and unitless house coordinates. The Swiss end-two extension adds two local adjacent transitions; all three emitted boards in that five-shot targeted scan match their official diagrams in postscore comparison. A first Canada–China transfer using the same scan rule produced two partial boards and zero complete boards from five shots. In selected later China development checks, estimated stone-body contact points match three of three diagram symbols under a 180° camera hypothesis, and a provisional fusion of the preceding shot’s overhead and wide views also matches three of three. Those targeted results do not revise the first-transfer score. The frozen wide-contact route initially catches one of two Swiss stones; a postscore blue-ring proposal recovers both. Stone positions alone fit opposite camera orientations, but the asymmetric painted button emblem independently indicates a 180° reversal in all 12 of 12 selected frame pairs for each China and Swiss handoff. Under that source-only orientation, wide-to-overhead contact overlap is one of one in China and two of two in Swiss; a provisional three-stone China union remains outside the state export. In five predeclared Slovakia windows, the revised rule sees only isolated wide frames and emits no stable contact tracks. The existing house detectors accept none of 57 sampled Norway delivery-view frames, so this emblem cue is not currently an early throw-gate router. Detection coverage, temporal continuity and perspective mapping are not independently validated. Every exported snapshot remains incomplete/unknown from video and not simulation-ready. No delivered-stone identity or physical state transition is established. <a href="validation/official-shot-sequence/WIDE-VIEW-PERSPECTIVE-EVIDENCE.md">Inspect the coverage finding</a>.',
    )
    html = html.replace(
        "no new shot window is recovered. Phase correction was postscore on "
        "Swiss. No independent labels or event F1; not promoted. ",
        "no new shot window is recovered. A selected follow-up camera-motion "
        "check finds relative movement in S123, yet one association step makes "
        "up 96.9% of its leading track path; S519 has no reliable registration "
        "pair. Possible internal edits also fall below the frozen cut threshold. "
        "A separate selected Swiss pan has 11 distributed motion steps but only "
        "7.3 px maximum camera-relative residual, so track continuity alone "
        "cannot veto it. "
        "Phase correction was postscore on Swiss. No independent labels or event "
        "F1; not promoted. ",
    )
    html = html.replace(
        '<a href="validation/curlobserver-learned-probe/cap-patch-crossmatch-v1/NONORIGIN-PHASE-V2.md">Audit</a></td></tr>',
        '<a href="validation/curlobserver-learned-probe/cap-patch-crossmatch-v1/NONORIGIN-PHASE-V2.md">Audit</a> · '
        '<a href="validation/curlobserver-learned-probe/cap-patch-crossmatch-v1/china-nonorigin-camera-relative-postscore.json">Motion diagnostic</a> · '
        '<a href="validation/curlobserver-learned-probe/cap-patch-crossmatch-v1/china-nonorigin-track-continuity-postscore.json">Track diagnostic</a> · '
        '<a href="validation/curlobserver-learned-probe/cap-patch-crossmatch-v1/nonorigin-track-continuity-development.json">Cross-recording check</a></td></tr>',
    )
    html = html.replace(
        "<tr><td><b>Public stone-box clips</b>",
        "<tr><td><b>Full China track-quality audit</b><small>All 102 existing cap-corroborated camera windows</small></td>"
        "<td><b>15/102 supported</b><small>42 visually ambiguous-colour abstentions</small></td>"
        "<td>Distributed cap motion plus camera-relative movement is a useful extra cue when present, but most candidate windows lack this combined evidence.</td>"
        "<td>After correcting an audit-only track replay mismatch, 12/43 known-colour windows associated with delayed counters have combined support. A hard gate would discard 31 of those windows. This is pipeline coverage, not independent event recall; the source was previously exposed. "
        '<a href="validation/curlobserver-learned-probe/cap-patch-crossmatch-v1/CHINA-CAP-TRACK-QUALITY-FULL.md">Full audit</a></td></tr>\n'
        "<tr><td><b>Public stone-box clips</b>",
    )
    html = html.replace(
        "<tr><td><b>Public stone-box clips</b>",
        "<tr><td><b>Colour provenance in China ledger</b><small>112 existing event candidates</small></td>"
        "<td><b>39 counter-derived</b><small>Both visual colours supported; 3 still unresolved</small></td>"
        "<td>The fused ledger already assigns a delayed-counter colour to 39 of the 42 visually ambiguous candidates. The new export records whether each colour came from visual motion, a counter, both, or neither.</td>"
        "<td>Another 10 candidate colours come from counters without corroborated visual candidates. Counter linkage is conditioned on adjacent motion and does not prove delivered-stone identity or event F1. "
        '<a href="validation/curlobserver-learned-probe/china-full-transfer/CHINA-EVENT-COLOUR-PROVENANCE.md">Provenance audit</a></td></tr>\n'
        "<tr><td><b>Public stone-box clips</b>",
    )
    html = html.replace(
        '<div class="notice alert"><strong>Latest transfer:',
        '<figure class="figure full"><img src="__EDIT_IMAGE__" '
        'alt="Two pairs of China broadcast frames show camera views changing within camera-shot windows S123 and S519.">'
        "<figcaption>Possible edits missed by the conservative cut threshold: "
        "at 1606.0 s and 7029.4 s the broadcast switches camera views inside "
        "existing shot windows. A full-source diagnostic proposes 58 additional "
        "China edits in 55 shots, versus six in Switzerland; 29 China proposals "
        "fall within existing same-shot cap-track intervals. The Swiss scan also "
        "fires on non-cut visual changes, so these are review candidates, not "
        "new confirmed boundaries. Background registration fails on all 64 "
        "proposed pairs, including Swiss non-cuts, and cannot resolve them alone. "
        "The unchanged rule proposes ten more edits in Norway and 17 in "
        "Slovakia; temporal isolation ranks seven and 13, yet misses some "
        "visible dissolves. "
        '<a href="validation/curlobserver-learned-probe/china-full-transfer/POSSIBLE-EDIT-FULL.md">Inspect the audit</a>.'
        '</figcaption></figure><div class="notice alert"><strong>Latest transfer:',
    )
    board_coverage = json.loads(CHINA_BOARD_EVENT_COVERAGE.read_text())
    if (
        board_coverage["window_count"] != 8
        or board_coverage["windows_with_partial_board"] != 5
        or board_coverage["grounded_event_present_count"] != 6
        or board_coverage["board_windows_missing_grounded_event_count"] != 2
    ):
        raise ValueError("China board/event coverage changed: review the report")
    rescue = json.loads(HELD_RESCUE.read_text())
    if [
        (row["official_game_code"], row["provisional_rescue_count"]) for row in rescue["games"]
    ] != [("PREL000101", 0), ("PREL000102", 3), ("PREL000103", 0)]:
        raise ValueError("Held-origin recovery proposals changed: review the report")
    travel_rescue = json.loads(TRAVEL_RESCUE.read_text())
    if [
        (row["official_game_code"], row["travel_proposal_count"]) for row in travel_rescue["games"]
    ] != [("PREL000101", 5), ("PREL000102", 21), ("PREL000103", 3)]:
        raise ValueError("Travel recovery proposals changed: review the report")
    reconciliation = json.loads(TRAVEL_RECONCILIATION.read_text())
    if (
        sum(row["possible_same_throw_pair_count"] for row in reconciliation["games"]) != 17
        or sum(
            row["relation_counts"].get("adjacent_visual_colour_conflict", 0)
            for row in reconciliation["games"]
        )
        != 13
    ):
        raise ValueError("Travel-origin reconciliation changed: review the report")
    relink = json.loads(CAP_VISUAL_RELINK.read_text())
    if (
        sum(row["new_link_count"] for row in relink["games"]) != 21
        or sum(row["new_colour_conflict_count"] for row in relink["games"]) != 16
        or [row["candidate_count_unchanged"] for row in relink["games"]] != [115, 112, 116]
    ):
        raise ValueError("Cap visual/counter re-link changed: review the report")
    union = json.loads(PROVISIONAL_UNION.read_text())
    china_board_union = json.loads(CHINA_BOARD_UNION.read_text())
    if (
        [row["provisional_event_count"] for row in union["games"]] != [117, 123, 116]
        or china_board_union["partial_board_windows_with_event"] != 5
        or china_board_union["partial_board_windows_overlapping_travel"] != 1
    ):
        raise ValueError("Provisional event/board union changed: review the report")
    full_review = json.loads(FULL_REVIEW_SEGMENTS.read_text())
    if [row["review_segment_count"] for row in full_review["games"]] != [117, 123, 116]:
        raise ValueError("Full-match review segment coverage changed: review the report")
    ice_tiebreak = json.loads(ICE_TIEBREAK.read_text())
    ice_norway = json.loads(ICE_TIEBREAK_NORWAY.read_text())
    if (
        sum(row["multi_option_counter_count"] for row in ice_tiebreak["games"]) != 10
        or sum(row["unique_ice_choice_count"] for row in ice_tiebreak["games"]) != 1
        or ice_norway["ambiguous_counter_count"] != 1
        or ice_norway["unique_ice_choice_count"] != 0
    ):
        raise ValueError("Ice tie-break transfer changed: review the report")
    chronology = json.loads(CHRONOLOGY_TIEBREAK.read_text())
    if (
        [row["ambiguous_counter_count"] for row in chronology["games"]] != [2, 3, 4, 1]
        or [row["unique_chronological_choice_count"] for row in chronology["games"]] != [0, 1, 1, 1]
        or sum(row["existing_link_temporal_conflict_count"] for row in chronology["games"]) != 6
    ):
        raise ValueError("Counter chronology audit changed: review the report")
    order = json.loads(SEQUENCE_ORDER.read_text())
    if (
        [row["multi_option_counter_count"] for row in order["games"]] != [3, 3, 4, 1]
        or [row["unique_order_proposal_count"] for row in order["games"]] != [1, 0, 3, 0]
        or sum(row["anchor_reversal_count"] for row in order["games"]) != 3
    ):
        raise ValueError("Counter sequence-order audit changed: review the report")
    order_colour = json.loads(ORDER_COLOUR_SCREEN.read_text())
    slovakia_order_colour = next(
        row for row in order_colour["games"] if row["recording_code"] == "PREL000103"
    )
    if (
        slovakia_order_colour["visual_colour_conflict_count"] != 1
        or slovakia_order_colour["visual_colour_abstention_count"] != 1
    ):
        raise ValueError("Order/colour screen changed: review the report")
    held_colour = json.loads(SLOVAKIA_HELD_COLOUR.read_text())
    by_held_shot = {row["shot_id"]: row for row in held_colour["shot_rows"]}
    if (
        held_colour["selected_counter_count"] != 4
        or held_colour["unique_candidate_shot_count"] != 13
        or sum(row["unique_held_colour"] is not None for row in held_colour["shot_rows"]) != 6
        or by_held_shot["S372"]["unique_held_colour"] != "yellow"
        or by_held_shot["S411"]["unique_held_colour"] != "yellow"
    ):
        raise ValueError("Slovakia held-colour scan changed: review the report")
    release_passages = json.loads(SLOVAKIA_RELEASE_PASSAGES.read_text())
    release_shots = {
        row["shot_id"]: row["unique_passage_colour"]
        for row in release_passages["shot_rows"]
        if row["unique_passage_colour"] is not None
    }
    if release_passages["unique_candidate_shot_count"] != 13 or release_shots != {
        "S287": "yellow",
        "S374": "red",
        "S411": "yellow",
    }:
        raise ValueError("Slovakia release-passage audit changed: review the report")
    sample_support = json.loads(COUNTER_SAMPLE_SUPPORT.read_text())
    if (
        sum(row["raw_counter_event_count"] for row in sample_support["games"]) != 420
        or sum(row["both_contexts_visible_count"] for row in sample_support["games"]) != 400
        or sum(row["both_expected_fraction_at_least_0_75_count"] for row in sample_support["games"])
        != 58
    ):
        raise ValueError("Counter raw-sample support changed: review the report")
    release_coverage = json.loads(SLOVAKIA_RELEASE_COVERAGE.read_text())
    if (
        release_coverage["provisional_event_count"] != 116
        or release_coverage["unique_passage_event_count"] != 34
        or release_coverage["colour_conflict_count"] != 1
        or sum(row["colour_relation"] == "agrees_with_ledger" for row in release_coverage["rows"])
        != 30
    ):
        raise ValueError("Slovakia full-candidate release coverage changed: review the report")
    swiss_release = json.loads(SWISS_RELEASE_TRANSFER.read_text())
    china_release = json.loads(CHINA_RELEASE_TRANSFER.read_text())
    if (
        swiss_release["provisional_event_count"] != 117
        or swiss_release["unique_passage_event_count"] != 46
        or swiss_release["colour_conflict_count"] != 0
        or china_release["provisional_event_count"] != 123
        or china_release["unique_passage_event_count"] != 31
        or china_release["colour_conflict_count"] != 1
    ):
        raise ValueError("Swiss/China release transfer changed: review the report")
    source_colour = json.loads(CROSS_VIEW_SOURCE_COLOUR.read_text())
    if (
        sum(row["source_colour_concordance_count"] for row in source_colour["games"]) != 16
        or sum(row["source_colour_ledger_unknown_count"] for row in source_colour["games"]) != 4
        or sum(row["source_colour_ledger_conflict_count"] for row in source_colour["games"]) != 1
    ):
        raise ValueError("Two-view source-colour handoff changed: review the report")
    temporal = json.loads(TWO_VIEW_TEMPORAL.read_text())
    temporal_rows = [row for game in temporal["games"] for row in game["rows"]]
    if (
        len(temporal_rows) != 16
        or any(row["qualifying_strict_track_count"] != 1 for row in temporal_rows)
        or any(
            row["qualifying_track_camera_motion_status"] != ["camera_motion_unresolved"]
            for row in temporal_rows
        )
        or min(row["cut_to_receiving_motion_s"] for row in temporal_rows) != 0.2
        or max(row["cut_to_receiving_motion_s"] for row in temporal_rows) != 4.8
    ):
        raise ValueError("Two-view temporal handoff changed: review the report")
    background = json.loads(S593_BACKGROUND.read_text())
    if (
        background["event_id"] != "VISUAL-S593"
        or background["unmasked"]["inliers"] != 11
        or background["target_excluded"]["tracked_features"] != 7
        or background["target_excluded"]["reliable_by_existing_rule"]
    ):
        raise ValueError("S593 background audit changed: review the report")
    release_board = json.loads(RELEASE_BOARD_HANDOFF.read_text())
    if (
        release_board["partial_board_count"] != 9
        or release_board["unique_counter_linked_event_count"] != 9
        or release_board["boards_with_unique_within_view_release_cue"] != 0
    ):
        raise ValueError("Release/board overlap changed: review the report")
    held_shot_board = json.loads(HELD_SHOT_BOARD_HANDOFF.read_text())
    if (
        held_shot_board["partial_board_count"] != 9
        or held_shot_board["unique_counter_linked_event_count"] != 9
        or held_shot_board["boards_with_unique_within_view_release_cue"] != 1
        or [
            row["counter_id"]
            for row in held_shot_board["rows"]
            if row["release_cue_status"] == "cue_precedes_board"
        ]
        != ["B57"]
    ):
        raise ValueError("Held-shot release/board overlap changed: review the report")
    scoped_release = json.loads(SHOT_SCOPED_RELEASE.read_text())
    if (
        scoped_release["provisional_event_count"] != 356
        or scoped_release["unique_scoped_cue_count"] != 111
        or [game["unique_scoped_cue_count"] for game in scoped_release["games"]] != [45, 32, 34]
    ):
        raise ValueError("Shot-scoped release ledger changed: review the report")
    outside = json.loads(OUTSIDE_UNION_CUES.read_text())
    rescue = json.loads(OUTSIDE_UNION_PROPOSALS.read_text())
    if (
        outside["selected_shot_count"] != 71
        or outside["raw_passage_shot_count"] != 3
        or outside["unique_ice_supported_shot_count"] != 2
        or rescue["proposal_count"] != 2
        or {row["origin_shot_id"] for row in rescue["proposals"]} != {"S392", "S216"}
    ):
        raise ValueError("Outside-union origin-cue discovery changed: review the report")
    outside_receiving = json.loads(OUTSIDE_UNION_RECEIVING.read_text())
    if outside_receiving["proposal_count"] != 2 or any(
        not row["hard_cut_verified"]
        or row["decision"]["status"] != "unique_strict_postcut_motion"
        or row["decision"]["colour"] != "red"
        or row["physical_stone_identity_verified"]
        for row in outside_receiving["rows"]
    ):
        raise ValueError("Outside-union receiving-view audit changed: review the report")
    rescue_union = json.loads(SOURCE_RESCUE_UNION_V2.read_text())
    rescue_review = json.loads(SOURCE_RESCUE_REVIEW_V2.read_text())
    if (
        rescue_union["total_provisional_event_count"] != 358
        or rescue_union["source_only_rescue_count"] != 2
        or rescue_review["total_review_segment_count"] != 358
        or rescue_review["source_only_rescue_review_count"] != 2
        or [game["provisional_event_count"] for game in rescue_union["games"]] != [118, 124, 116]
    ):
        raise ValueError("Additive source-rescue union changed: review the report")
    handoff_v2 = json.loads(EVENT_HANDOFF_V2.read_text())
    if (
        handoff_v2["event_count"] != 358
        or handoff_v2["unique_release_cue_count"] != 113
        or handoff_v2["two_view_source_colour_agreement_count"] != 18
        or handoff_v2["partial_board_link_count"] != 9
        or handoff_v2["release_cue_and_partial_board_count"] != 1
    ):
        raise ValueError("V2 event evidence handoff changed: review the report")
    unassigned_scan = json.loads(ALL_UNASSIGNED_SCAN.read_text())
    preorigin_rescue = json.loads(PREORIGIN_TRAVEL_RESCUE.read_text())
    if (
        unassigned_scan["scanned_shot_count"] != 1351
        or unassigned_scan["raw_passage_shot_count"] != 8
        or unassigned_scan["unique_ice_supported_shot_count"] != 4
        or unassigned_scan["model_negative_unique_ice_supported_shot_count"] != 4
        or sum(game["earlier_positive_shots_reproduced"] for game in unassigned_scan["games"]) != 69
        or preorigin_rescue["triaged_candidate_count"] != 4
        or preorigin_rescue["proposal_count"] != 1
        or preorigin_rescue["proposals"][0]["proposal_id"] != "TRAVEL-B02"
    ):
        raise ValueError("Full unassigned-shot scan or triage changed: review the report")
    union_v3 = json.loads(PREORIGIN_UNION_V3.read_text())
    review_v3 = json.loads(PREORIGIN_REVIEW_V3.read_text())
    handoff_v3 = json.loads(EVENT_HANDOFF_V3.read_text())
    if (
        union_v3["total_provisional_event_count"] != 359
        or union_v3["preorigin_travel_rescue_count"] != 1
        or review_v3["total_review_segment_count"] != 359
        or review_v3["preorigin_travel_review_count"] != 1
        or handoff_v3["event_count"] != 359
        or handoff_v3["unique_release_cue_count"] != 113
        or handoff_v3["two_view_source_colour_agreement_count"] != 18
        or handoff_v3["partial_board_link_count"] != 9
        or handoff_v3["preorigin_travel_without_release_count"] != 1
    ):
        raise ValueError("V3 B02 event handoff changed: review the report")
    slot_audit = json.loads(COUNTER_SLOT_V3.read_text())
    if (
        slot_audit["official_shot_count"] != 349
        or slot_audit["provisional_event_count"] != 359
        or slot_audit["counter_linked_event_count"] != 308
        or slot_audit["counter_anchored_unique_official_slot_count"] != 300
        or slot_audit["uncovered_official_slot_count"] != 49
        or slot_audit["duplicate_counter_slot_count"] != 6
        or slot_audit["noncounter_candidate_count"] != 51
    ):
        raise ValueError("V3 counter-slot coverage changed: review the report")
    sequence_audit = json.loads(SEQUENCE_V3.read_text())
    if (
        sequence_audit["provisional_candidate_count"] != 359
        or sequence_audit["official_shot_count"] != 349
        or sequence_audit["clean_fixed_counter_anchor_count"] != 275
        or sequence_audit["candidate_status_counts"]
        != {
            "same_match_in_every_optimum": 330,
            "skipped_in_every_optimum": 15,
            "ambiguous_optimal_alignment": 14,
        }
        or sequence_audit["official_status_counts"]
        != {
            "same_match_in_every_optimum": 330,
            "ambiguous_optimal_alignment": 9,
            "unmatched_in_every_optimum": 10,
        }
    ):
        raise ValueError("V3 sequence audit changed: review the report")
    s593 = json.loads(S593_SENSITIVITY.read_text())
    if (
        s593["event_id"] != "VISUAL-S593"
        or s593["source_evidence"]["within_view_release_cue_colour"] != "yellow"
        or s593["source_evidence"]["receiving_view_colour"] != "yellow"
        or s593["baseline"]["minimum_cost"] != 8
        or s593["source_yellow_scenario"]["minimum_cost"] != 4
        or s593["baseline"]["optimal_path_count"] != 2
        or s593["source_yellow_scenario"]["optimal_path_count"] != 1
    ):
        raise ValueError("S593 colour sensitivity changed: review the report")
    review_queue = json.loads(SEQUENCE_REVIEW_QUEUE.read_text())
    if (
        review_queue["row_count"] != 25
        or review_queue["source_release_cue_present_in_skipped_candidates"] != 4
    ):
        raise ValueError("V3 sequence review queue changed: review the report")
    receiving_gap = json.loads(CHINA_E01_RECEIVING_GAP.read_text())
    if (
        receiving_gap["official_gap_id_for_selection_only"] != "PREL000102-E01-S14"
        or not receiving_gap["cut_at_915_4_s_verified"]
        or receiving_gap["postcut_strict_track_counts"] != {"red": 0, "yellow": 0}
        or receiving_gap["origin_scan"][0]["raw_passage_count"] != 0
        or receiving_gap["origin_scan"][1]["raw_passage_count"] != 0
    ):
        raise ValueError("China E01 receiving-gap diagnostic changed: review the report")
    html = html.replace(
        '<div class="speaker-notes">The official PDF boards let us check future reconstruction;',
        '<div class="card" style="margin-top:18px"><span class="eyebrow">Grounded event handoff</span>'
        "<h3>21 of 112 China candidates have a possible camera edit crossing a cap track</h3>"
        "<p>The new export preserves each event and its visual-versus-counter colour source, "
        "then marks tentative internal view changes and crossing cap tracks. "
        "Another 14 candidates have a possible edit without a crossing track; "
        "77 have no edit proposed by this threshold. None has verified physical "
        "stone identity, exact release time, continuous trajectory or a "
        "simulation-ready state. "
        '<a href="validation/curlobserver-learned-probe/china-full-transfer/EVENT-GROUNDING-ENVELOPE.md">Inspect the handoff</a>.</p></div>'
        '<div class="notice alert"><strong>Event-to-board coverage:</strong> In eight '
        "previously selected China board windows, five contain partial boards. "
        "The earlier counter-linked ledger covers all eight, but only three of "
        "the five board-bearing windows appear in the newer 112-candidate "
        "cap-fusion envelope. One omitted window has a legacy event colour "
        "conflict. A missing cap-fusion candidate does not mean a throw was "
        "absent, and a shared counter does not verify the delivered stone. "
        "An existing held-cap-over-ice cue gives a provisional recovery for "
        "one omitted counter, B57. A separate receiving-view cue shows "
        "provisional yellow motion for B26 after its counter update, but leaves "
        "release identity and the board transition unknown. Across the three "
        "exposed 2022 recordings, the held-cue rule proposes three "
        "China additions and none in Switzerland or Slovakia. "
        "Across all three recordings, 17 of 29 travel proposals sit after an "
        "existing visual-only candidate; 13 pairs disagree on colour. "
        "The existing one-to-one linking rule attaches 21 counters to existing "
        "candidates without raising event counts, exposing 16 colour conflicts. "
        "A separate deduplicated union has 117, 123 and 116 provisional "
        "candidates across the three recordings. All five selected China "
        "board-bearing windows now have a counter-linked candidate; only B26 "
        "has board frames overlapping observed travel. These are source "
        "bookkeeping links, not verified physical transitions. "
        '<a href="validation/official-shot-sequence/PROVISIONAL-EVENT-EVIDENCE-UNION.md">Inspect the union</a> '
        'and <a href="validation/official-shot-sequence/CHINA-BOARD-UNION-HANDOFF.md">board handoff</a>.</div>'
        '<div class="speaker-notes">The official PDF boards let us check future reconstruction;',
    )
    html = html.replace(
        '<div class="demo-links" style="margin-top:18px">',
        '<div class="demo-links" style="margin-top:18px">'
        '<a href="prototype/full-match-event-review-v3/index.html">'
        '<span class="eyebrow">Full-match viewer</span>'
        "<strong>Review 359 provisional event windows ↗</strong>"
        "<span>Three source recordings; search TRAVEL-B02 for the new receiving-travel "
        "case, SOURCE-S392 or SOURCE-S216 for source-only releases, or China B26. "
        "These clips are review windows, not validated physical throw segments.</span></a>",
    )
    html = html.replace(
        "<tr><td><b>Public stone-box clips</b>",
        "<tr><td><b>Official-sequence diagnostic</b><small>Audit only, all three exposed 2022 recordings</small></td>"
        "<td><b>15 candidates / 10 official slots</b><small>Persistent skip or gap in every minimum-cost alignment</small></td>"
        "<td>With 275 clean counter anchors fixed, an order-and-colour comparison places "
        "330 candidates at the same official shot in every optimal alignment. "
        "The 15 persistent skips and 10 persistent gaps provide a focused video-review queue. "
        "Four skipped candidates still have a distinct source-video release cue, "
        "so skips cannot be removed wholesale.</td>"
        "<td>The official sequence and alignment cost are postscore diagnostics, not "
        "independent physical throw labels or runtime detector inputs. "
        '<a href="validation/official-shot-sequence/PWG2022-V3-SEQUENCE-SKIP-SOURCE-REVIEW.md">Four source-frame reviews</a> · '
        '<a href="validation/official-shot-sequence/pwg2022-v3-sequence-review-queue-development.json">25-case queue</a> · '
        '<a href="validation/official-shot-sequence/pwg2022-v3-official-sequence-diagnostic-development.json">sequence audit data</a></td></tr>\n'
        "<tr><td><b>Receiving-view recall lead</b><small>Selected China end-one gap</small></td>"
        "<td><b>Visible red travel / 0 accepted tracks</b><small>Cut at 915.4 s</small></td>"
        "<td>Between two candidate windows, the broadcast shows a China delivery setup, "
        "a close-up that hides release, then a red stone traveling toward the house. "
        "The full-source origin passage scan and strict post-cut scanner both abstain.</td>"
        "<td>Official E01-S14 selected this postscore inspection; the physical shot link "
        "and cross-view identity are not verified. This is a recall lead, not a measured "
        'false negative. <a href="validation/official-shot-sequence/CHINA-E01-S14-RECEIVING-GAP.md">Source frames and diagnostic</a></td></tr>\n'
        "<tr><td><b>China S593 colour check</b><small>Selected end-eight sensitivity</small></td>"
        "<td><b>8 to 4 edit cost</b><small>Red ledger versus yellow source cues</small></td>"
        "<td>The ledger colours S593 red; its within-view release cue and receiving-view "
        "track are yellow. Changing only that candidate colour makes S593 align to "
        "official shot E08-S13 in the unique lowest-cost sequence.</td>"
        "<td>This supports a provisional source-colour correction, not verified "
        "cross-camera stone identity or event F1. The frozen candidate union is unchanged. "
        '<a href="validation/official-shot-sequence/PREL000102-VISUAL-S593-sequence-skip-source-review.jpg">Source frames</a> · '
        '<a href="validation/official-shot-sequence/china-s593-sequence-colour-sensitivity-development.json">sensitivity data</a></td></tr>\n'
        "<tr><td><b>Official-shot slot coverage proxy</b><small>Three exposed 2022 recordings</small></td>"
        "<td><b>359 candidates / 349 official shots</b><small>300 distinct counter-anchored slots</small></td>"
        "<td>Across the three matches, 308 counter-linked candidates reach 300 "
        "distinct official slots. Forty-nine official slots have no counter-linked "
        "candidate; six slots receive multiple counter links. China has 125 "
        "candidates for 125 official shots yet still has 11 slots without a "
        "counter-linked candidate.</td>"
        "<td>Unlinked video events may cover those slots, and counters can flicker. "
        "This is a proxy coverage diagnostic, not physical throw precision, "
        "recall or F1. "
        '<a href="validation/official-shot-sequence/PWG2022-V3-COUNTER-SLOT-COVERAGE.md">Slot audit</a></td></tr>\n'
        "<tr><td><b>Public stone-box clips</b>",
        1,
    )
    html = html.replace(
        "<tr><td><b>Public stone-box clips</b>",
        "<tr><td><b>Full unassigned-shot source scan</b><small>Three exposed 2022 recordings</small></td>"
        "<td><b>1,351 camera shots</b><small>8 raw cues; 4 ice-supported</small></td>"
        "<td>All four supported cues were in shots rejected by the origin model. "
        "Three Swiss cases sit immediately before existing red candidates or in "
        "house-side motion. China S28 is red receiving travel after unassigned "
        "delivery-like S27; raw red counter B02 follows at 383 s.</td>"
        "<td>The postscore triage proposes one new travel-only B02 candidate, "
        "included provisionally in a separate 359-event union. Its receiving-view trigger is "
        "not a release time, and physical identity remains unverified. "
        '<a href="validation/official-shot-sequence/PWG2022-ALL-UNASSIGNED-SHOT-SCAN.md">Source audit</a> · '
        '<a href="validation/official-shot-sequence/china-s28-receiving-travel-review.jpg">China frames</a></td></tr>\n'
        "<tr><td><b>Public stone-box clips</b>",
        1,
    )
    html = html.replace(
        "<tr><td><b>Public stone-box clips</b>",
        "<tr><td><b>Integrated event evidence handoff</b><small>Additive v3 candidate union</small></td>"
        "<td><b>359 event records</b><small>113 release cues; 18 two-view colour agreements</small></td>"
        "<td>One provenance record per candidate now joins source-shot release timing, "
        "receiving-view evidence, review window and any partial board link. Nine events "
        "have a board link; only China B57 has both a release cue and board link. "
        "B02 has red receiving travel but no visible release cue.</td>"
        "<td>All physical release times, persistent stone identities, settle times and "
        "continuous trajectories remain unknown. None is simulation-ready; the nine "
        "board links are counter-based. "
        '<a href="validation/official-shot-sequence/PWG2022-EVENT-EVIDENCE-HANDOFF-V3.md">Handoff and limits</a></td></tr>\n'
        "<tr><td><b>Public stone-box clips</b>",
        1,
    )
    html = html.replace(
        "<tr><td><b>Public stone-box clips</b>",
        "<tr><td><b>Outside-union origin-cue discovery</b><small>Three exposed 2022 recordings</small></td>"
        "<td><b>2 rescue proposals</b><small>71 origin-like shots scanned; 3 raw cues</small></td>"
        "<td>Swiss S392 and China S216 show red held-to-motion passages absent from the "
        "frozen 356-candidate union. Each is followed after a verified cut by one strict red "
        "receiving-view motion track. A Swiss close-up triggers the raw cue but fails "
        "the existing ice-context check.</td>"
        "<td>Camera-motion registration is unresolved in both receiving views. These "
        "are source-visible recall leads, not independently labeled throws or "
        "measured F1. An additive 358-candidate union includes them provisionally, "
        "without official-shot links or physical identity claims. "
        '<a href="validation/official-shot-sequence/PWG2022-OUTSIDE-UNION-ORIGIN-CUES.md">Source audit</a> · '
        '<a href="validation/official-shot-sequence/FULL-MATCH-EVENT-REVIEW-SEGMENTS-V2.md">V2 review method</a> · '
        '<a href="validation/official-shot-sequence/pwg2022-outside-union-origin-cues-review.jpg">Frame panel</a></td></tr>\n'
        "<tr><td><b>Public stone-box clips</b>",
        1,
    )
    html = html.replace(
        "<tr><td><b>Public stone-box clips</b>",
        "<tr><td><b>Ice-context ambiguity tie-break</b><small>Three exposed 2022 recordings, then Norway</small></td>"
        "<td><b>1/10 selected</b><small>Norway: 0/1</small></td>"
        "<td>Visible ice separates one Swiss delivery view from a close-up; the "
        "unchanged rule abstains on the Norway ambiguity.</td>"
        "<td>A view cue cannot establish delivered-stone identity and was not "
        "promoted as a throw decision. "
        '<a href="validation/official-shot-sequence/AMBIGUOUS-COUNTER-ICE-TIEBREAK.md">Source audit</a></td></tr>\n'
        "<tr><td><b>Public stone-box clips</b>",
    )
    html = html.replace(
        "<tr><td><b>Public stone-box clips</b>",
        "<tr><td><b>Counter chronology diagnostic</b><small>Four exposed 2022 recordings</small></td>"
        "<td><b>3/10 unique proposals</b><small>6 contrary existing links</small></td>"
        "<td>The previous broadcast counter update resolves three multi-option camera-shot assignments, "
        "including Norway B69 → S389. Source review supports that Norway choice.</td>"
        "<td>Counter graphics can lag the next delivery: six existing links violate the proposed ordering. "
        "No event ledger or physical F1 changes. "
        '<a href="validation/official-shot-sequence/COUNTER-CHRONOLOGY-TIEBREAK.md">Source audit</a></td></tr>\n'
        "<tr><td><b>Public stone-box clips</b>",
    )
    html = html.replace(
        "<tr><td><b>Public stone-box clips</b>",
        "<tr><td><b>Counter sequence-order audit</b><small>Four exposed 2022 recordings</small></td>"
        "<td><b>4/11 unique proposals</b><small>3 existing link reversals</small></td>"
        "<td>Neighbouring counter links constrain camera-shot options. A source-video held-cap "
        "scan now detects yellow in both new Slovakia delivery windows offered for red counters; "
        "the frozen post-cut audit calls one yellow and abstains on the other.</td>"
        "<td>Neither new link was added. The stronger within-view release cue fires in "
        "3/13 competing shots, including yellow S411 and red S374, but raw scoreboard "
        "counts flicker around B80/B81. Colour and order do not establish cross-view "
        "identity or an F1 gain. "
        '<a href="validation/official-shot-sequence/SLOVAKIA-AMBIGUOUS-RELEASE-PASSAGES.md">Source audit</a></td></tr>\n'
        "<tr><td><b>Public stone-box clips</b>",
    )
    html = html.replace(
        "<tr><td><b>Public stone-box clips</b>",
        "<tr><td><b>Raw scoreboard support</b><small>Four exposed 2022 recordings</small></td>"
        "<td><b>58/400 high support</b><small>420 emitted raw updates</small></td>"
        "<td>Only 58 updates with readable samples on both sides have at least 0.75 exact "
        "before- and after-state support; one-second icon reads often flicker.</td>"
        "<td>A hard stability cutoff would throw away much of the delayed-counter evidence. "
        "This is counter-reader coverage, not physical throw accuracy. "
        '<a href="validation/official-shot-sequence/COUNTER-SAMPLE-SUPPORT.md">Source audit</a></td></tr>\n'
        "<tr><td><b>Public stone-box clips</b>",
    )
    html = html.replace(
        "<tr><td><b>Public stone-box clips</b>",
        "<tr><td><b>Within-view release-cue transfer</b><small>Three exposed full-match candidate ledgers</small></td>"
        "<td><b>111/356 shot-scoped cues</b><small>Swiss 45; China 32; Slovakia 34</small></td>"
        "<td>The held-to-motion scan gives source-linked cue times. Scoping to declared "
        "camera shots removes Swiss B48 and recovers China B57; the original broad scan "
        "also totalled 111 but had different cases. There are 101 ledger-colour "
        "agreements, two conflicts and eight unknown colours.</td>"
        "<td>31.2% is candidate coverage, not physical throw recall. A cap passage does not "
        "prove cross-view identity or an exact release. "
        '<a href="validation/official-shot-sequence/PWG2022-SHOT-SCOPED-RELEASE-CUES.md">Source audit</a></td></tr>\n'
        "<tr><td><b>Two-view source-colour handoff</b><small>Strict post-cut cue plus within-view passage</small></td>"
        "<td><b>16 source agreements</b><small>4 unknown ledger colours; 1 conflict</small></td>"
        "<td>China S593 has yellow delivery and receiving-view cues against a red ledger colour; "
        "the receiving track begins 0.6 s after the cut.</td>"
        "<td>All 16 tracks lack reliable background registration. At S593, excluding the "
        "yellow target leaves only seven tracked background features; lowering the fit "
        "threshold would be unsafe. The main ledger retains red for review. "
        '<a href="validation/official-shot-sequence/PWG2022-RELEASE-TRANSFER-AND-COLOUR.md">Evidence handoff</a></td></tr>\n'
        "<tr><td><b>Public stone-box clips</b>",
    )
    html = html.replace(
        "<tr><td><b>Public stone-box clips</b>",
        "<tr><td><b>Release-to-board overlap</b><small>Nine video-derived partial boards</small></td>"
        "<td><b>1/9 scoped cue links</b><small>9/9 provisional counter links</small></td>"
        "<td>China B57 has one red held-to-motion passage at 3459.8 s when scanned within "
        "its held-origin camera shot. Its broad multi-shot window had two passages and "
        "abstained; the other eight board links still lack a unique cue.</td>"
        "<td>The B57 cue, receiving-view travel and later partial board form a provisional "
        "timed evidence chain through a delayed counter, not verified delivered-stone "
        "identity or a physical state transition. This is coverage, not throw recall. "
        '<a href="validation/official-shot-sequence/PWG2022-RELEASE-BOARD-COVERAGE.md">Source audit</a></td></tr>\n'
        "<tr><td><b>Public stone-box clips</b>",
    )
    from build_t11_joined_figure import build_figure

    html = html.replace(
        '<section class="section" id="roadmap">',
        '<section class="section" id="roadmap">'
        '<div class="notice"><strong>Two-stage filter prototype:</strong> '
        "Raw throw proposals now remain in a review ledger when a confirmation gate withholds them. "
        "On the exposed Estonia excerpt, the older speed cutoff withheld three labelled passages; "
        "one common image-context gate now retains them as automated candidates on that already studied video. This is a development diagnostic, "
        "not independent full-match scores. "
        '<a href="validation/two-stage-throw-audit/index.html">Open the three-video audit</a>.</div>',
        1,
    )
    html = html.replace("__T11_JOINED__", png_data(build_figure()))
    html = html.replace(
        "__T11_RELEASE__", jpeg_data(ROOT / "prototype/throw-analysis/T11-release-visibility.jpg")
    )
    html = html.replace(
        "__CROSS_IMAGE__", jpeg_data(ROOT / "prototype/cross-view/T11-evidence.jpg")
    )
    html = html.replace(
        "__CONFLICT_IMAGE__", jpeg_data(MEETING / "canada-norway-conflict-frame.jpg")
    )
    html = html.replace("__EDIT_IMAGE__", jpeg_data(MEETING / "china-possible-edit-examples.jpg"))
    from translate_progress_report_fr import translate_html

    ENGLISH_OUTPUT.write_text(html)
    french = translate_html(html)
    OUTPUT.write_text(french)
    print(f"Wrote {OUTPUT} ({len(french):,} characters) and English source")


if __name__ == "__main__":
    main()
