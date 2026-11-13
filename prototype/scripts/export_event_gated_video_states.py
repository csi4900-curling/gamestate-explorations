"""Export source-video partial board states for every reviewed China event.

The Norway comparison covers one selected end. No official diagram or
postscore comparison enters this state export.
"""

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
NORWAY_REVIEW = (
    ROOT / "validation/curlobserver-learned-probe/canada-norway-full-transfer/fused-linked.json"
)
COVERAGE = BASE / "event-gated-overhead-image-coverage-first.json"
CHINA = BASE / "china-full-match-event-gated-source-video-boards-first.json"
NORWAY = BASE / "norway-end2-event-gated-source-video-boards-first.json"
OUTPUT = BASE / "event-gated-video-state-observations-first.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def board_stones(scan_row):
    return [
        {
            "local_observation_id": f"V{i:02}",
            "colour": stone["colour"],
            "position_house_radii": [
                stone["canonical_lateral_house_radii"],
                stone["longitudinal_house_radii"],
            ],
            "first_seen_s": stone["first_seen_s"],
            "last_seen_s": stone["last_seen_s"],
            "supporting_frame_count": stone["supporting_frame_count"],
            "max_position_spread_house_radii": stone["max_position_spread_house_radii"],
            "persistent_stone_identity": None,
            "in_play_status": "unknown_from_video",
        }
        for i, stone in enumerate(scan_row["stable_partial_board"], 1)
    ]


def export_game(game, scan, coverage, *, selected_counter_ids=None):
    scans = {r["counter_id"]: r for r in scan["rows"]}
    views = {r["counter_id"]: r for r in coverage["rows"]}
    if scan["source_video_sha256"] != game["source_sha256"]:
        raise ValueError("Review and scan source videos differ")
    if coverage["source_video_sha256"] != game["source_sha256"]:
        raise ValueError("Review and coverage source videos differ")
    segments = game["segments"]
    if selected_counter_ids is not None:
        segments = [s for s in segments if s["counter_id"] in selected_counter_ids]
        if {s["counter_id"] for s in segments} != set(selected_counter_ids) or len(segments) != len(
            selected_counter_ids
        ):
            raise ValueError("Selected counter events missing from review")
    rows = []
    for event in segments:
        counter_id = event["counter_id"]
        scan_row = scans.get(counter_id)
        stones = board_stones(scan_row) if scan_row else []
        if stones:
            view = views[counter_id]
            if any(s["first_seen_s"] < event["delivery_window_s"][1] + 4 for s in stones):
                raise ValueError(f"{counter_id}: a stone predates the source-only event gate")
            observation_interval = [
                min(s["first_seen_s"] for s in stones),
                max(s["last_seen_s"] for s in stones),
            ]
            coverage_status = {
                "image_bound_house_envelope_seen": view["any_frame_house_envelope"],
                "image_bound_extended_envelope_seen": view["any_frame_extended_envelope"],
                "actual_ice_coverage": "unverified",
            }
        else:
            observation_interval = None
            coverage_status = None
        rows.append(
            {
                "event_id": event["event_id"],
                "counter_id": counter_id,
                "candidate_class": event["candidate_class"],
                "event_evidence": event["event_evidence"],
                "throw_colour": event["colour_reconciliation"]["colour"]
                if "colour_reconciliation" in event
                else event.get("colour"),
                "throw_colour_provenance": event.get("colour_reconciliation"),
                "delivery_window_s": event["delivery_window_s"],
                "counter_anchor_s": scan_row["counter_time_s"] if scan_row else None,
                "state_status": "partial_video_board_observed"
                if stones
                else "no_stable_video_board",
                "observation_interval_s": observation_interval,
                "coordinate_frame": {
                    "origin": "detected_house_button",
                    "unit": "detected_outer_house_radius",
                    "orientation": "inferred_from_source_overhead_views",
                    "metric_scale_status": "unvalidated",
                },
                "image_coverage": coverage_status,
                "completeness": "unknown_from_video",
                "physical_settle_time_s": None,
                "persistent_stone_id_status": "unverified",
                "stones": stones,
                "simulation_ready": False,
            }
        )
    return {
        "recording_code": game["official_game_code"],
        "source_video_sha256": game["source_sha256"],
        "event_count": len(rows),
        "partial_board_count": sum(bool(r["stones"]) for r in rows),
        "unobserved_board_count": sum(not r["stones"] for r in rows),
        "stone_observation_count": sum(len(r["stones"]) for r in rows),
        "rows": rows,
    }


def build():
    review = json.loads(REVIEW.read_text())
    handoff = json.loads(HANDOFF.read_text())
    norway_review = json.loads(NORWAY_REVIEW.read_text())
    coverage = json.loads(COVERAGE.read_text())
    scans = {"china": json.loads(CHINA.read_text()), "norway_end2": json.loads(NORWAY.read_text())}
    views = {r["recording"]: r for r in coverage["recordings"]}
    if (
        scans["china"]["event_review_sha256"] != digest(REVIEW)
        or scans["norway_end2"]["event_review_sha256"] != digest(NORWAY_REVIEW)
        or views["china"]["scan_sha256"] != digest(CHINA)
        or views["norway_end2"]["scan_sha256"] != digest(NORWAY)
    ):
        raise ValueError("Review or image-coverage provenance differs from source-only scans")
    games = {g["official_game_code"]: g for g in review["games"]}
    china_handoff = next(g for g in handoff["games"] if g["recording_code"] == "PREL000102")
    if china_handoff["source_sha256"] != games["PREL000102"]["source_sha256"]:
        raise ValueError("China two-view handoff comes from another source")
    handoff_rows = {r["event_id"]: r for r in china_handoff["rows"]}
    if len(handoff_rows) != len(china_handoff["rows"]):
        raise ValueError("Duplicate China handoff event IDs")
    china_game = dict(games["PREL000102"])
    china_game["segments"] = []
    for segment in games["PREL000102"]["segments"]:
        evidence = handoff_rows[segment["event_id"]]
        if (
            segment["colour"] != evidence["event_colour"]
            or segment["counter_id"] != evidence["counter_id"]
        ):
            raise ValueError("China event and two-view handoff disagree")
        china_game["segments"].append(
            {
                **segment,
                "event_evidence": event_evidence_tier(
                    segment["counter_id"], evidence["release_cue"], evidence["receiving_view"]
                ),
                "colour_reconciliation": reconcile_event_colour(
                    segment["colour"], evidence["release_cue"], evidence["receiving_view"]
                ),
            }
        )
    norway_game = {
        "official_game_code": "canada-norway-2022-end2",
        "source_sha256": norway_review["source_sha256"],
        "segments": [
            {
                "event_id": event["shot_id"],
                "counter_id": event["counter_id"],
                "candidate_class": event["status"],
                "colour": event["colour"],
                "event_evidence": event_evidence_tier(event["counter_id"], {}, {}),
                "delivery_window_s": event["delivery_window_s"],
            }
            for event in norway_review["events"]
        ],
    }
    records = [
        export_game(china_game, scans["china"], views["china"]),
        export_game(
            norway_game,
            scans["norway_end2"],
            views["norway_end2"],
            selected_counter_ids={f"B{i:02}" for i in range(16, 32)},
        ),
    ]
    return {
        "status": "source_video_partial_game_state_export_no_official_diagram_inputs",
        "input_sha256": {
            "review": digest(REVIEW),
            "handoff": digest(HANDOFF),
            "colour_reconciliation": digest(ROOT / "prototype/source_colour_reconciliation.py"),
            "event_evidence_tiers": digest(ROOT / "prototype/event_evidence_tiers.py"),
            "norway_review": digest(NORWAY_REVIEW),
            "coverage": digest(COVERAGE),
            "china_scan": digest(CHINA),
            "norway_scan": digest(NORWAY),
            "runner": digest(Path(__file__)),
        },
        "recordings": records,
        "limitations": [
            "Board positions are anonymous, unitless and may include out-of-play objects.",
            "No exact release or settle time or persistent stone identity was measured.",
            "Image bounds are optimistic and do not prove complete ice coverage.",
            "Norway export is one selected end only.",
            "No row is simulation-ready.",
        ],
    }


def main():
    if OUTPUT.exists():
        raise SystemExit("Output exists; preserve first source-video state export")
    result = build()
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n")
    print(
        [
            {
                key: record[key]
                for key in (
                    "recording_code",
                    "event_count",
                    "partial_board_count",
                    "unobserved_board_count",
                    "stone_observation_count",
                )
            }
            for record in result["recordings"]
        ]
    )


if __name__ == "__main__":
    main()
