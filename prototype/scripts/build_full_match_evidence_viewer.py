"""Freeze a file://-compatible full-match evidence review dataset."""

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256  # noqa: E402


def unique(rows, key):
    result = {row[key]: row for row in rows}
    if len(result) != len(rows):
        raise ValueError(f"Duplicate {key}")
    return result


def build(timeline, tracklets, frozen, development, development_motion,
          comparisons, marker_audit, source_review, additional_review=None):
    events = timeline["timeline"]
    states = unique(tracklets["candidate_states"], "candidate_id")
    frozen_decisions = unique(frozen["decisions"], "candidate_id")
    development_decisions = unique(development["decisions"], "candidate_id")
    development_paths = unique(development_motion["rows"], "candidate_id")
    comparison_rows = unique(comparisons["comparisons"], "after_candidate_id")
    review_rows = unique(source_review["rows"], "candidate_id")
    additional_review_id = additional_review["candidate_id"] if additional_review else None
    ids = [event["candidate_id"] for event in events]
    if len(ids) != len(set(ids)) or ids != sorted(ids, key=lambda pid: next(
            x["passage_time_s"] for x in events if x["candidate_id"] == pid)):
        raise ValueError("Timeline IDs are duplicated or out of time order")
    if (set(frozen_decisions) != set(development_decisions) or
            set(frozen_decisions) != set(development_paths) or
            set(states) != {row["id"] for row in frozen["events"]}):
        raise ValueError("Screen, development path or board-state coverage differs")
    if any(not development_decisions[pid]["accepted"]
           for pid in frozen_decisions if frozen_decisions[pid]["accepted"]):
        raise ValueError("Development branch lost a frozen acceptance")
    if set(review_rows) != {pid for pid in frozen_decisions
                            if development_decisions[pid]["accepted"] and
                            not frozen_decisions[pid]["accepted"]}:
        raise ValueError("Development source review coverage differs")
    if additional_review and (additional_review_id not in frozen_decisions or
            not frozen_decisions[additional_review_id]["accepted"] or
            additional_review["source_sha256"] != timeline["source_sha256"] or
            additional_review["screen_status"] !=
            frozen_decisions[additional_review_id]["status"] or
            not additional_review["review_conclusion"].startswith("false_positive_") or
            additional_review_id in review_rows):
        raise ValueError("Additional false-positive review does not match accepted candidate")
    runs = marker_audit["display_run_rows"]
    output = []
    for event in events:
        pid, time_s = event["candidate_id"], event["passage_time_s"]
        frozen_decision = frozen_decisions.get(pid)
        development_decision = development_decisions.get(pid)
        if event["event_status"] == "source_reviewed_false_positive" or (
                pid == additional_review_id):
            group = "reviewed_false_positive"
        elif frozen_decision and frozen_decision["accepted"]:
            group = "frozen_candidate"
        elif development_decision and development_decision["accepted"]:
            group = "development_only"
        elif frozen_decision:
            group = "screen_abstention"
        else:
            group = "outside_corridor"
        path_source = None
        path = []
        observed = event["observed_receiving_motion"]
        if observed and observed["samples"]:
            path_source = "frozen"
            path = observed["samples"]
        elif group == "development_only":
            proposal = development_paths[pid]["selection"].get("path") or []
            if not proposal:
                raise ValueError(f"Development candidate lacks path: {pid}")
            path_source = "postscore_development"
            path = [{"source_time_s": node["source_time_s"],
                     "ground_position_m_conditional": node["ground_position_m"]}
                    for node in proposal]
        board = states.get(pid)
        if board and board["partial_board_status"] != (
                event["post_event_board"] or {}).get("status"):
            raise ValueError(f"Board status differs for {pid}")
        run = next((row for row in runs
                    if row["first_marker_hit_s"] <= time_s <=
                    row["last_marker_hit_s"]), None)
        output.append({
            "id": pid,
            "time_s": time_s,
            "colour": event["candidate_colour"],
            "group": group,
            "frozen_status": event["event_status"],
            "screen_decision": event["screen_decision"],
            "development_decision": development_decision["status"]
                if development_decision else None,
            "receiving_view": event["receiving_view"]
                or (development_paths[pid]["receiving_view"]
                    if pid in development_paths else None),
            "displayed_end_run": run["displayed_end"] if run else None,
            "path_source": path_source,
            "path": [{"time_s": node["source_time_s"],
                      "x_m": node["ground_position_m_conditional"][0],
                      "y_m": node["ground_position_m_conditional"][1]}
                     for node in path],
            "board_status": board["partial_board_status"] if board else None,
            "stones": [{
                "colour": stone["colour"],
                "x_m": stone["view_local_ground_position_m"][0],
                "y_m": stone["view_local_ground_position_m"][1],
                "tracklet_id": stone["observation_tracklet_id"],
                "supporting_frames": stone["supporting_frame_count"],
            } for stone in board["observed_stones"]] if board else [],
            "comparison": {
                "before_id": comparison_rows[pid]["before_candidate_id"],
                "status": comparison_rows[pid]["status"],
                "matched_count": len(comparison_rows[pid].get(
                    "matched_observations", [])),
            } if pid in comparison_rows else None,
            "review_frame": ("../left-short-path-source-review/" +
                             review_rows[pid]["frame_file"])
                if pid in review_rows else
                (additional_review["review_frame"]["file"]
                 if pid == additional_review_id else
                ("../source-review/s143-6380.5.jpg"
                 if group == "reviewed_false_positive" else None)),
            "review_note": (additional_review["basis"]
                            if pid == additional_review_id else
                            ((event.get("source_review") or {}).get("basis")
                             if group == "reviewed_false_positive" else None)),
            "physical_throw_identity_verified": False,
            "complete_game_state": False,
            "simulation_ready": False,
        })
    lengths = Counter(row["group"] for row in output)
    return {
        "status": "postscore_interactive_evidence_review_not_game_truth",
        "source_id": timeline["source_id"],
        "source_sha256": timeline["source_sha256"],
        "source_interval_s": timeline["source_interval_s"],
        "counts": dict(lengths),
        "events": output,
        "tracklets": [{
            "id": row["tracklet_id"],
            "colour": row["colour"],
            "view": row["receiving_view"],
            "candidate_ids": [node["candidate_id"] for node in row["observations"]],
        } for row in tracklets["tracklets"]],
        "limitations": [
            "Candidate markers are observed passages, not verified throw boundaries.",
            "Positions are conditional view-local projections; board coverage and physical stone identity are unverified.",
            "The nine development-only paths were selected after inspecting this recording.",
        ],
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("timeline", "tracklets", "frozen_screen", "development_screen",
                 "development_motion", "comparisons", "marker_audit", "source_review",
                 "video"):
        p.add_argument("--" + name.replace("_", "-"), type=Path, required=True)
    p.add_argument("--additional-review", type=Path)
    p.add_argument("--additional-review-evidence", type=Path)
    p.add_argument("--output-dir", type=Path, required=True)
    a = p.parse_args()
    paths = {name: getattr(a, name) for name in (
        "timeline", "tracklets", "frozen_screen", "development_screen",
        "development_motion", "comparisons", "marker_audit", "source_review")}
    if a.additional_review:
        paths["additional_review"] = a.additional_review
        if not a.additional_review_evidence:
            p.error("Additional review requires its supporting evidence artifact")
        paths["additional_review_evidence"] = a.additional_review_evidence
    elif a.additional_review_evidence:
        p.error("Additional review evidence has no associated review")
    data = {name: json.loads(path.read_text()) for name, path in paths.items()}
    if (data["tracklets"]["timeline_sha256"] != file_sha256(a.timeline) or
            data["timeline"]["screen_sha256"] != file_sha256(a.frozen_screen) or
            data["tracklets"]["comparisons_sha256"] != file_sha256(a.comparisons) or
            data["frozen_screen"]["source_sha256"] != data["timeline"]["source_sha256"] or
            data["development_screen"]["source_sha256"] != data["timeline"]["source_sha256"] or
            data["development_screen"]["motion_sha256"] != file_sha256(a.development_motion) or
            data["marker_audit"]["source_sha256"] != data["timeline"]["source_sha256"] or
            file_sha256(a.video) != data["timeline"]["source_sha256"]):
        p.error("Source, screen, tracklet or video provenance differs")
    if a.additional_review:
        review = data["additional_review"]
        frame = a.output_dir / review["review_frame"]["file"]
        if (review["high_resolution_source_sha256"] !=
                data["development_motion"]["high_resolution_source_sha256"] or
                file_sha256(frame) != review["review_frame"]["sha256"] or
                review["cross_corridor_overlap_sha256"] !=
                file_sha256(a.additional_review_evidence) or
                review["candidate_id"] not in
                data["additional_review_evidence"]["accepted_selected_candidate_ids_with_pair"]):
            p.error("Additional review source or frame hash differs")
    result = build(data["timeline"], data["tracklets"],
                   data["frozen_screen"], data["development_screen"],
                   data["development_motion"], data["comparisons"],
                   data["marker_audit"], data["source_review"],
                   data.get("additional_review"))
    a.output_dir.mkdir(parents=True, exist_ok=True)
    data_path = a.output_dir / "data.js"
    data_path.write_text("window.CURLING_FULL_MATCH_EVIDENCE = " +
                         json.dumps(result, separators=(",", ":")) + ";\n")
    provenance = {
        "status": "generated_file_compatible_review_data",
        "input_sha256": {name: file_sha256(path) for name, path in paths.items()},
        "video_sha256": file_sha256(a.video),
        "runner_sha256": file_sha256(Path(__file__)),
        "data_js_sha256": file_sha256(data_path),
        "viewer_files_sha256": {
            name: file_sha256(a.output_dir / name)
            for name in ("index.html", "style.css", "app.js")
            if (a.output_dir / name).exists()
        },
        "counts": result["counts"],
    }
    (a.output_dir / "provenance.json").write_text(
        json.dumps(provenance, indent=2) + "\n")
    print(len(result["events"]), "candidate rows", result["counts"])


if __name__ == "__main__":
    main()
