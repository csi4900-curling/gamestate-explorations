"""Build a file-compatible viewer dataset for the 91-candidate development branch."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "validation/throw-event-benchmark/canada-czech-2024/full-match-review"


def digest(path):
    value = sha256()
    with path.open("rb") as source:
        while block := source.read(1024 * 1024):
            value.update(block)
    return value.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "timeline",
        "integrated_screen",
        "frozen_screen",
        "tracklets",
        "comparisons",
        "marker_audit",
        "video",
        "output_dir",
    ):
        parser.add_argument(f"--{name.replace('_', '-')}", type=Path, required=True)
    parser.add_argument(
        "--pre-split-proposals", type=Path, help="Optional partial pre-split review proposals"
    )
    parser.add_argument(
        "--pre-split-boards",
        type=Path,
        help="Optional partial boards for pre-split review proposals",
    )
    args = parser.parse_args()
    if args.output_dir.exists():
        parser.error("Viewer output already exists")
    paths = {
        name: getattr(args, name)
        for name in (
            "timeline",
            "integrated_screen",
            "frozen_screen",
            "tracklets",
            "comparisons",
            "marker_audit",
        )
    }
    data = {name: json.loads(path.read_text()) for name, path in paths.items()}
    timeline = data["timeline"]
    integrated = data["integrated_screen"]
    frozen = data["frozen_screen"]
    tracklets = data["tracklets"]
    comparisons = data["comparisons"]
    marker = data["marker_audit"]
    if (
        timeline["screen_sha256"] != digest(args.integrated_screen)
        or integrated["frozen_screen_sha256"] != digest(args.frozen_screen)
        or tracklets["timeline_sha256"] != digest(args.timeline)
        or tracklets["comparisons_sha256"] != digest(args.comparisons)
        or comparisons["screen_sha256"] != digest(args.integrated_screen)
        or marker["source_sha256"] != timeline["source_sha256"]
        or digest(args.video) != timeline["source_sha256"]
    ):
        parser.error("Viewer input provenance differs")
    frozen_by = {row["candidate_id"]: row for row in frozen["decisions"]}
    integrated_by = {row["candidate_id"]: row for row in integrated["decisions"]}
    state_by = {row["candidate_id"]: row for row in tracklets["candidate_states"]}
    comparison_by = {row["after_candidate_id"]: row for row in comparisons["comparisons"]}
    added = set(integrated["added_candidate_ids"])
    pre_split = None
    pre_split_by = {}
    duplicate_by = {}
    review_board_by = {}
    if args.pre_split_boards and not args.pre_split_proposals:
        parser.error("Pre-split boards require pre-split proposals")
    if args.pre_split_proposals:
        pre_split = json.loads(args.pre_split_proposals.read_text())
        if (
            pre_split["source_id"] != timeline["source_id"]
            or pre_split["screen_sha256"] != digest(args.integrated_screen)
            or pre_split["unique_proposal_count"] != len(pre_split["proposals"])
        ):
            parser.error("Pre-split proposal provenance differs")
        pre_split_by = {row["candidate_id"]: row for row in pre_split["proposals"]}
        for row in pre_split["proposals"]:
            for duplicate_id in row["duplicate_candidate_ids"]:
                if duplicate_id in duplicate_by:
                    parser.error("Repeated pre-split duplicate")
                duplicate_by[duplicate_id] = row["candidate_id"]
        if (
            len(pre_split_by) != len(pre_split["proposals"])
            or (set(pre_split_by) & set(duplicate_by))
            or not (set(pre_split_by) | set(duplicate_by)).issubset(integrated_by)
        ):
            parser.error("Invalid pre-split candidate coverage")
        if any(integrated_by[pid]["accepted"] for pid in set(pre_split_by) | set(duplicate_by)):
            parser.error("Pre-split proposal overlaps accepted event")
    if args.pre_split_boards:
        review_boards = json.loads(args.pre_split_boards.read_text())
        review_board_by = {row["candidate_id"]: row for row in review_boards["rows"]}
        if (
            review_boards["proposals_sha256"] != digest(args.pre_split_proposals)
            or review_boards["source_sha256"] != timeline["source_sha256"]
            or len(review_board_by) != len(review_boards["rows"])
            or set(review_board_by) != set(pre_split_by)
            or any(
                row["post_throw_settle_verified"] or row["persistent_stone_ids_verified"]
                for row in review_boards["rows"]
            )
        ):
            parser.error("Pre-split board provenance or coverage differs")
    if len(state_by) != len(tracklets["candidate_states"]) or set(state_by) != {
        event["id"] for event in integrated["events"]
    }:
        parser.error("Tracklet state coverage differs")
    output_events = []
    for event in timeline["timeline"]:
        pid = event["candidate_id"]
        frozen_decision = frozen_by.get(pid)
        decision = integrated_by.get(pid)
        if event["event_status"] == "source_reviewed_false_positive":
            group = "reviewed_false_positive"
        elif pid in pre_split_by:
            group = "pre_split_review"
        elif pid in duplicate_by:
            group = "pre_split_duplicate"
        elif pid in added:
            group = "development_only"
        elif frozen_decision and frozen_decision["accepted"]:
            group = "frozen_candidate"
        elif decision:
            group = "screen_abstention"
        else:
            group = "outside_corridor"
        if decision and event["screen_decision"] != decision["status"]:
            raise ValueError(f"Screen decision differs for {pid}")
        state = state_by.get(pid)
        board = event["post_event_board"]
        if (state is None) != (board is None):
            raise ValueError(f"Board and state differ for {pid}")
        if state and state["partial_board_status"] != board["status"]:
            raise ValueError(f"Board status differs for {pid}")
        review_board = review_board_by.get(pid)
        if review_board and (board is not None or state is not None):
            parser.error(f"Pre-split board overlaps accepted board: {pid}")
        time_s = event["passage_time_s"]
        run = next(
            (
                row
                for row in marker["display_run_rows"]
                if row["first_marker_hit_s"] <= time_s <= row["last_marker_hit_s"]
            ),
            None,
        )
        observed = event["observed_receiving_motion"] or {}
        path = observed.get("samples") or []
        proposal = pre_split_by.get(pid)
        if proposal:
            path = [
                {
                    "source_time_s": node["source_time_s"],
                    "ground_position_m_conditional": node["ground_position_m"],
                }
                for node in proposal["prefix_samples"]
            ]
        comparison = comparison_by.get(pid)
        review_frame = None
        if pid in added:
            review_frame = f"../source-review/{pid.lower()}-path-review.jpg"
        elif pid in pre_split_by or pid in duplicate_by:
            review_frame = (
                "../../gap-review/ambiguous-prefix-review/"
                + f"{(duplicate_by.get(pid) or pid).lower()}-prefix.jpg"
            )
        elif pid == "S96":
            review_frame = "../../accepted-low-score-source-review/s96-path-review.jpg"
        elif pid == "S143":
            review_frame = "../../source-review/s143-6380.5.jpg"
        output_events.append(
            {
                "id": pid,
                "time_s": time_s,
                "colour": event["candidate_colour"],
                "group": group,
                "frozen_status": frozen_decision["status"] if frozen_decision else None,
                "screen_decision": event["screen_decision"],
                "development_decision": decision["status"] if decision else None,
                "receiving_view": event["receiving_view"],
                "displayed_end_run": run["displayed_end"] if run else None,
                "path_source": (
                    "pre_split_partial"
                    if proposal
                    else "postscore_development"
                    if pid in added
                    else "frozen"
                )
                if path
                else None,
                "path": [
                    {
                        "time_s": node["source_time_s"],
                        "x_m": node["ground_position_m_conditional"][0],
                        "y_m": node["ground_position_m_conditional"][1],
                    }
                    for node in path
                ],
                "board_status": state["partial_board_status"] if state else None,
                "stones": [
                    {
                        "colour": stone["colour"],
                        "x_m": stone["view_local_ground_position_m"][0],
                        "y_m": stone["view_local_ground_position_m"][1],
                        "tracklet_id": stone["observation_tracklet_id"],
                        "supporting_frames": stone["supporting_frame_count"],
                    }
                    for stone in state["observed_stones"]
                ]
                if state
                else [],
                "observation_scope": "camera_local_tracklet" if state else None,
                "comparison": {
                    "before_id": comparison["before_candidate_id"],
                    "status": comparison["status"],
                    "matched_count": len(comparison.get("matched_observations", [])),
                }
                if comparison
                else None,
                "review_frame": review_frame,
                "review_note": (event.get("source_review") or {}).get("basis"),
                "first_ambiguity_time_s": proposal["first_ambiguity_time_s"] if proposal else None,
                "positive_prefix_patch_count": proposal["positive_patch_count"]
                if proposal
                else None,
                "duplicate_of": duplicate_by.get(pid),
                "physical_throw_identity_verified": False,
                "complete_game_state": False,
                "simulation_ready": False,
            }
        )
        if review_board:
            board_observation = review_board["board"]
            output_events[-1]["board_status"] = board_observation["status"]
            output_events[-1]["stones"] = [
                {
                    "colour": stone["colour"],
                    "x_m": stone["view_local_ground_position_m"][0],
                    "y_m": stone["view_local_ground_position_m"][1],
                    "tracklet_id": stone["local_observation_id"],
                    "supporting_frames": stone["supporting_frame_count"],
                }
                for stone in board_observation["stones"]
            ]
            output_events[-1]["observation_scope"] = "candidate_local_only"
            output_events[-1]["board_tail_excluded_duplicate_ids"] = review_board[
                "tail_clock_excluded_exact_duplicate_ids"
            ]
    if len(output_events) != 147 or [event["id"] for event in output_events] != [
        event["candidate_id"] for event in timeline["timeline"]
    ]:
        parser.error("Raw timeline coverage differs")
    counts = dict(Counter(row["group"] for row in output_events))
    if (
        counts.get("frozen_candidate") != 77
        or counts.get("development_only") != 12
        or counts.get("reviewed_false_positive") != 2
    ):
        parser.error("Unexpected accepted candidate groups")
    if pre_split and (
        counts.get("pre_split_review") != len(pre_split_by)
        or counts.get("pre_split_duplicate") != len(duplicate_by)
    ):
        parser.error("Pre-split review groups differ")
    result = {
        "status": "postscore_91_candidate_interactive_evidence_not_game_truth",
        "source_id": timeline["source_id"],
        "source_sha256": timeline["source_sha256"],
        "source_interval_s": timeline["source_interval_s"],
        "counts": counts,
        "events": output_events,
        "tracklets": [
            {
                "id": row["tracklet_id"],
                "colour": row["colour"],
                "view": row["receiving_view"],
                "candidate_ids": [node["candidate_id"] for node in row["observations"]],
            }
            for row in tracklets["tracklets"]
        ],
        "limitations": [
            "These are candidate passages, not verified throws or physical release times.",
            "All boards and path positions are conditional camera-local observations.",
            "No complete game state, physical stone identity, or simulation-ready throw is shown.",
        ],
    }
    args.output_dir.mkdir(parents=True)
    for name in ("index.html", "style.css", "app.js"):
        shutil.copyfile(TEMPLATE / name, args.output_dir / name)
    index = args.output_dir / "index.html"
    html = index.read_text()
    html = html.replace('src="../source-360p.mp4"', 'src="../../source-360p.mp4"')
    html = html.replace("Full-match evidence explorer", "Wider-bound full-match evidence explorer")
    html = html.replace("../FULL-MATCH-STAGE2-RESULTS.md", "../../FULL-MATCH-STAGE2-RESULTS.md")
    html = html.replace("../LEFT-SHORT-PATH-RESULTS.md", "../../LEFT-BOUND-STATE-HANDOFF.md")
    if pre_split:
        html = html.replace(
            "Wider-bound full-match evidence explorer", "Full-match pre-split evidence explorer"
        )
        html = html.replace(
            '<option value="screen_abstention">Screen abstentions</option>',
            '<option value="pre_split_review">Pre-split motion review</option>\n'
            '        <option value="pre_split_duplicate">Duplicate pre-split trigger</option>\n'
            '        <option value="screen_abstention">Screen abstentions</option>',
        )
        html = html.replace(
            "../../LEFT-BOUND-STATE-HANDOFF.md", "../../PRE-SPLIT-PROPOSAL-RESULTS.md"
        )
    if review_board_by:
        html = html.replace(
            "An O-number is an image-observation tracklet, not a verified physical stone ID.",
            "An O-number is an image-observation tracklet; a V-number is local to one review board. Neither is a verified physical stone ID.",
        )
    index.write_text(html)
    app = args.output_dir / "app.js"
    js = app.read_text().replace(
        "A postscore short-path rule recovered a moving, stone-like proposal here. It was designed after seeing this recording; the early passage-to-stone association and physical throw identity are unverified.",
        "The wider left-camera search bound recovered a source-visible stone path here. This remains a postscore candidate: passage-to-stone identity and the full throw are unverified.",
    )
    if pre_split:
        js = js.replace(
            'development_only: "Development only",',
            'development_only: "Development only",\n'
            '    pre_split_review: "Pre-split review",\n'
            '    pre_split_duplicate: "Same pre-split motion",',
        )
        js = js.replace(
            'if (event.group === "frozen_candidate")\n',
            'if (event.group === "pre_split_review")\n'
            "      return `The source shows a moving stone before the path splits at ${event.first_ambiguity_time_s.toFixed(1)} s. "
            "${event.positive_prefix_patch_count} sampled prefix patches passed the frozen appearance model. "
            "The event screen still abstains; delivery identity, post-split stone identity and board outcome are unverified.`;\n"
            '    if (event.group === "pre_split_duplicate")\n'
            "      return `This early trigger repeats the same observed prefix as ${event.duplicate_of}. "
            "It is one motion observation, not a second throw.`;\n"
            '    if (event.group === "frozen_candidate")\n',
        )
        js = js.replace(
            'event.path_source === "postscore_development" ? "postscore development path" : "frozen path"',
            'event.path_source === "pre_split_partial" ? "pre-split partial path; stops before identity ambiguity" : '
            'event.path_source === "postscore_development" ? "postscore development path" : "frozen path"',
        )
    if review_board_by:
        js = js.replace(
            '<td><button type="button" data-tracklet="${esc(stone.tracklet_id)}">${esc(stone.tracklet_id)}</button></td>',
            '<td>${event.observation_scope === "candidate_local_only" ? esc(stone.tracklet_id) : '
            '`<button type="button" data-tracklet="${esc(stone.tracklet_id)}">${esc(stone.tracklet_id)}</button>`}</td>',
        )
        js = js.replace(
            "`${event.stones.length} stable stone proposals · camera-local positions · completeness unknown`",
            '`${event.stones.length} stable stone proposals · ${event.observation_scope === "candidate_local_only" ? "one review window only" : "camera-local positions"} · completeness unknown`',
        )
    app.write_text(js)
    if pre_split:
        style = args.output_dir / "style.css"
        style.write_text(
            style.read_text()
            + "\n.candidate-button.group-pre_split_review .stripe { background:#6745a2; }\n"
            ".candidate-button.group-pre_split_duplicate .stripe { background:#a79ab8; }\n"
            ".status-pill.pre_split_review { background:#eee8f8; color:#563982; }\n"
            ".status-pill.pre_split_duplicate { background:#f2eff5; color:#685c73; }\n"
        )
    data_path = args.output_dir / "data.js"
    data_path.write_text(
        "window.CURLING_FULL_MATCH_EVIDENCE = " + json.dumps(result, separators=(",", ":")) + ";\n"
    )
    provenance = {
        "status": "generated_file_compatible_91_candidate_review_data",
        "input_sha256": {name: digest(path) for name, path in paths.items()},
        "pre_split_proposals_sha256": digest(args.pre_split_proposals)
        if args.pre_split_proposals
        else None,
        "pre_split_boards_sha256": digest(args.pre_split_boards) if args.pre_split_boards else None,
        "video_sha256": digest(args.video),
        "runner_sha256": digest(Path(__file__)),
        "data_js_sha256": digest(data_path),
        "viewer_files_sha256": {
            name: digest(args.output_dir / name) for name in ("index.html", "style.css", "app.js")
        },
        "counts": counts,
    }
    (args.output_dir / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    print(len(output_events), "raw candidates", counts, len(result["tracklets"]), "tracklets")


if __name__ == "__main__":
    main()
