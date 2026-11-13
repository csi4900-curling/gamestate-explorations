"""Build an offline, single-match evidence dashboard from preserved v3 outputs."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.source_colour_reconciliation import reconcile_event_colour
from prototype.event_evidence_tiers import event_evidence_tier

BASE = ROOT / "validation/official-shot-sequence"
REVIEW = BASE / "pwg2022-full-match-event-review-segments-v3-preorigin-travel-development.json"
HANDOFF = BASE / "pwg2022-event-evidence-handoff-v3-development.json"
BOARDS = BASE / "pwg2022-video-partial-board-observations-v2.json"
FULL_BOARDS = BASE / "china-full-match-source-video-boards-first.json"
FULL_BOARD_SCORE = BASE / "china-full-match-video-board-first-score.json"
MOTION_PROBE = BASE / "china-all-counterless-motion-probe-first.json"
OFFICIAL = BASE / "pwg2022-official-shot-ledger.json"
ALIGNMENT = BASE / "pwg2022-official-counter-alignment.json"
DIAGRAMS = BASE / "pwg2022-official-board-diagrams.json"
OUTPUT = ROOT / "prototype/full-match-canada-china"
CODE = "PREL000102"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def unique(rows, key):
    indexed = {row[key]: row for row in rows}
    if len(indexed) != len(rows):
        raise ValueError(f"Duplicate {key}")
    return indexed


def build():
    review = json.loads(REVIEW.read_text())
    handoff = json.loads(HANDOFF.read_text())
    boards = json.loads(BOARDS.read_text())
    full_boards = json.loads(FULL_BOARDS.read_text())
    full_board_score = json.loads(FULL_BOARD_SCORE.read_text())
    motion_probe = json.loads(MOTION_PROBE.read_text())
    official = json.loads(OFFICIAL.read_text())
    alignment = json.loads(ALIGNMENT.read_text())
    diagrams = json.loads(DIAGRAMS.read_text())
    game = next(g for g in review["games"] if g["official_game_code"] == CODE)
    evidence = next(g for g in handoff["games"] if g["recording_code"] == CODE)
    reference = next(g for g in official["games"] if g["official_game_code"] == CODE)
    aligned = next(g for g in alignment["games"] if g["official_game_code"] == CODE)
    diagram_game = next(g for g in diagrams["games"] if g["official_game_code"] == CODE)
    source = ROOT / game["source_video_path"]
    if not source.exists() or digest(source) != game["source_sha256"]:
        raise ValueError("Full-match video is missing or differs from the reviewed source")
    if (
        game["source_sha256"] != evidence["source_sha256"]
        or game["source_sha256"] != reference["source_video_sha256"]
    ):
        raise ValueError("Source provenance differs across inputs")
    if (
        motion_probe["source_video_sha256"] != game["source_sha256"]
        or motion_probe["review_sha256"] != digest(REVIEW)
        or motion_probe["handoff_sha256"] != digest(HANDOFF)
    ):
        raise ValueError("Counterless motion probe provenance differs")
    reviews = unique(game["segments"], "event_id")
    evidence_rows = unique(evidence["rows"], "event_id")
    counter_rows = unique(aligned["counter_rows"], "counter_id")
    motion_rows = unique(motion_probe["rows"], "event_id")
    if len(motion_rows) != 9:
        raise ValueError("Counterless motion probe inventory changed")
    official_shots = unique(
        [shot for end in reference["ends"] for shot in end["shots"]], "official_shot_id"
    )
    reference_states = [
        {
            "official_shot_id": shot["official_shot_id"],
            "end": end["end"],
            "shot_number": index,
            "official_turn_direction": official_shots[shot["official_shot_id"]].get("rotation"),
            "diagram_delivery_side": shot["delivery_side"],
            "stones": [
                {
                    "colour": stone["colour"],
                    "position_house_radii": stone["house_radius_coordinates"],
                }
                for stone in shot["stones"]
            ],
            "review_flags": shot["review_flags"],
        }
        for end in diagram_game["ends"]
        for index, shot in enumerate(end["shots"], start=1)
    ]
    state_ids = {state["official_shot_id"] for state in reference_states}
    if len(reference_states) != reference["official_shot_count"] or len(state_ids) != len(
        reference_states
    ):
        raise ValueError("Official post-shot state count changed")
    if set(reviews) != set(evidence_rows):
        raise ValueError("Review windows and handoff events differ")
    video_boards = unique(
        [b for b in boards["observations"] if b["source_recording_code"] == CODE], "observation_id"
    )
    scanned_boards = unique(full_boards["rows"], "counter_id")
    if full_boards["source_video_sha256"] != game["source_sha256"] or full_board_score[
        "source_only_scan_sha256"
    ] != digest(FULL_BOARDS):
        raise ValueError("Full-match video board scan provenance changed")
    events = []
    for event_id, row in reviews.items():
        ev = evidence_rows[event_id]
        if (
            row["review_window_s"] != ev["review_window_s"]
            or row["delivery_window_s"] != ev["delivery_window_s"]
            or row["counter_id"] != ev["counter_id"]
            or row["colour"] != ev["event_colour"]
            or row["candidate_class"] != ev["candidate_class"]
        ):
            raise ValueError(f"Evidence mismatch: {event_id}")
        reconciled_colour = reconcile_event_colour(
            row["colour"], ev["release_cue"], ev["receiving_view"]
        )
        evidence_tier = event_evidence_tier(
            row["counter_id"], ev["release_cue"], ev["receiving_view"]
        )
        motion_row = motion_rows.get(event_id)
        if (row["counter_id"] is None) != (motion_row is not None):
            raise ValueError(f"Counterless motion probe join mismatch: {event_id}")
        if motion_row:
            candidates = [
                {
                    "colour": colour,
                    "first_seen_s": track["first_seen_s"],
                    "last_seen_s": track["last_seen_s"],
                    "span_px": track["span_px"],
                }
                for colour in ("red", "yellow")
                for track in motion_row["colour_tracks"][colour]
            ]
            motion_summary = {
                "status": "moving_cap_track_observed"
                if candidates
                else "no_supported_track_in_probe",
                "search_interval_s": motion_row["search_interval_s"],
                "tracks": sorted(candidates, key=lambda track: track["first_seen_s"]),
                "physical_throw_identity_verified": False,
            }
        else:
            motion_summary = None
        linked = []
        for link in ev["partial_board_links"]:
            board = video_boards[link["board_observation_id"]]
            if board["source_video_sha256"] != game["source_sha256"] or board["simulation_ready"]:
                raise ValueError("Linked board provenance or readiness changed")
            linked.append(
                {"source": "selected_temporal_board_prior", "link": link, "observation": board}
            )
        scanned = scanned_boards.get(row["counter_id"])
        if scanned and scanned["stable_partial_board"]:
            linked = [
                {
                    "source": "full_match_source_only_scan",
                    "link": {
                        "counter_id": row["counter_id"],
                        "join_status": "shared_counter_proxy",
                    },
                    "observation": {
                        "observation_interval_s": scanned["observation_interval_s"],
                        "simulation_ready": False,
                        "stones": [
                            {
                                "colour": stone["colour"],
                                "position_house_radii": [
                                    stone["canonical_lateral_house_radii"],
                                    stone["longitudinal_house_radii"],
                                ],
                                "supporting_frame_count": stone["supporting_frame_count"],
                                "max_position_spread_house_radii": stone[
                                    "max_position_spread_house_radii"
                                ],
                            }
                            for stone in scanned["stable_partial_board"]
                        ],
                    },
                }
            ]
        counter = counter_rows.get(row["counter_id"])
        reference_link = None
        if counter and counter["status"] in (
            "unique_colour_concordant",
            "unique_colour_concordant_amid_duplicate",
        ):
            if counter["official_shot_id"] not in state_ids:
                raise ValueError("Aligned counter points outside the official board reference")
            reference_link = {
                "official_shot_id": counter["official_shot_id"],
                "status": "broadcast_counter_order_proxy",
                "counter_status": counter["status"],
            }
        events.append(
            {
                "id": event_id,
                "class": row["candidate_class"],
                "colour": reconciled_colour["colour"],
                "colour_status": row["colour_status"]
                if reconciled_colour["status"] in ("unchanged", "two_view_concordant_no_revision")
                else reconciled_colour["status"],
                "colour_reconciliation": reconciled_colour,
                "event_evidence": evidence_tier,
                "counterless_motion_probe": motion_summary,
                "counter_id": row["counter_id"],
                "review_window_s": row["review_window_s"],
                "delivery_window_s": row["delivery_window_s"],
                "evidence_core_s": row["evidence_core_s"],
                "possible_edit_times_s": row["possible_internal_edit_times_s"],
                "camera_shots": row["review_shot_ids"],
                "release_cue": ev["release_cue"],
                "receiving_view": ev["receiving_view"],
                "partial_boards": linked,
                "official_reference_link": reference_link,
                "physical_release_time_s": ev["physical_release_time_s"],
                "physical_settle_time_s": ev["physical_settle_time_s"],
                "persistent_stone_id": ev["persistent_stone_id"],
                "continuous_trajectory": ev["continuous_trajectory"],
                "spin_observation": {
                    "status": "unmeasured",
                    "direction": None,
                    "revolutions": None,
                    "reason": "No handle-orientation time series has been validated for this event.",
                },
                "simulation_ready": ev["simulation_ready"],
            }
        )
    events.sort(key=lambda event: event["review_window_s"][0])
    if any(row["simulation_ready"] for row in events):
        raise ValueError("Unverified event marked simulation-ready")
    counts = Counter(event["class"] for event in events)
    return {
        "status": "full_match_provisional_event_and_partial_board_demo",
        "recording_code": CODE,
        "match": "Canada–China 2022",
        "source_video_path": "../../" + game["source_video_path"],
        "source_video_sha256": game["source_sha256"],
        "source_interval_s": game["source_interval_s"],
        "official_shot_count": reference["official_shot_count"],
        "provisional_event_count": len(events),
        "event_classes": dict(counts),
        "unique_release_cue_count": sum(e["release_cue"]["time_s"] is not None for e in events),
        "cross_view_colour_agreement_count": sum(
            e["receiving_view"]["status"] == "source_colour_concordant_identity_unverified"
            for e in events
        ),
        "source_two_view_colour_revision_count": sum(
            e["colour_reconciliation"]["status"]
            in ("source_two_view_colour_filled", "source_two_view_colour_corrected")
            for e in events
        ),
        "event_evidence_tiers": dict(Counter(e["event_evidence"]["tier"] for e in events)),
        "counterless_motion_probe_with_track_count": sum(
            e["counterless_motion_probe"] is not None
            and e["counterless_motion_probe"]["status"] == "moving_cap_track_observed"
            for e in events
        ),
        "partial_board_link_count": sum(len(e["partial_boards"]) for e in events),
        "full_scan_board_count": full_boards["rows_with_stable_board"],
        "prior_only_board_count": sum(
            bool(e["partial_boards"])
            and e["partial_boards"][0]["source"] == "selected_temporal_board_prior"
            for e in events
        ),
        "first_full_scan_board_score": {
            key: full_board_score[key]
            for key in (
                "scored_counter_count",
                "scored_rows_with_video_board",
                "scored_video_stone_count",
                "matched_stone_count",
                "complete_board_match_count",
            )
        },
        "counter_aligned_reference_link_count": sum(
            e["official_reference_link"] is not None for e in events
        ),
        "official_post_shot_states": reference_states,
        "simulation_ready_count": 0,
        "measured_spin_count": 0,
        "input_sha256": {
            "review": digest(REVIEW),
            "handoff": digest(HANDOFF),
            "video_boards": digest(BOARDS),
            "full_match_video_board_scan": digest(FULL_BOARDS),
            "full_match_video_board_score": digest(FULL_BOARD_SCORE),
            "official_shot_ledger": digest(OFFICIAL),
            "counter_alignment": digest(ALIGNMENT),
            "official_diagrams": digest(DIAGRAMS),
            "source_colour_reconciliation": digest(
                ROOT / "prototype/source_colour_reconciliation.py"
            ),
            "event_evidence_tiers": digest(ROOT / "prototype/event_evidence_tiers.py"),
            "counterless_motion_probe": digest(MOTION_PROBE),
            "builder": digest(Path(__file__)),
        },
        "events": events,
        "limitations": [
            "Official post-shot boards are an independent PDF reference, not states reconstructed from the video.",
            "Counter-to-official-shot links are broadcast-order proxies, not verified physical event matches or F1 labels.",
            "Review windows follow broadcast camera shots and include waiting; they are not exact physical throw segments.",
            "Release cues are observed proxy times, not exact physical release times.",
            "Partial boards have unknown completeness and unvalidated metric scale.",
            "No continuous physical trajectory, verified settle time, persistent stone identity, or simulation-ready state is established.",
        ],
    }


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    result = build()
    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    (OUTPUT / "results.json").write_text(payload)
    (OUTPUT / "data.js").write_text(
        "const MATCH_DATA = "
        + json.dumps(result, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
        + ";\n"
    )
    print(
        {
            k: result[k]
            for k in (
                "provisional_event_count",
                "official_shot_count",
                "unique_release_cue_count",
                "cross_view_colour_agreement_count",
                "partial_board_link_count",
                "counter_aligned_reference_link_count",
                "simulation_ready_count",
            )
        }
    )


if __name__ == "__main__":
    main()
