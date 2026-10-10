"""Read Beijing 2022 overlay changes without assuming a fixed camera view."""

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from broadcast_scoreboard import read_beijing_counts, ScoreboardEvents
from cache_contract import file_sha256
from stone_motion_fallback import verify_final_stone_motion, verify_stone_motion_in_interval


def single_decrement(before, after):
    """Return the colour of one decreasing counter, or None for an ambiguous change."""
    delta = [a - b for a, b in zip(before, after)]
    if delta == [1, 0]:
        return "red"
    if delta == [0, 1]:
        return "yellow"
    return None


def visual_event(evidence, colour, origin, **context):
    track = evidence["selected_track"]
    if track is None:
        return None
    start_t = track["points"][0]["time_s"]
    end_t = track["points"][-1]["time_s"]
    return {
        "colour": colour,
        "crossing_time_s": start_t,
        "evidence_interval_s": [start_t, end_t],
        "evidence_kind": origin,
        "release_time_s": None,
        "confirmed_at_s": end_t,
        "visual_track_span_px": track["span_px"],
        "visual_track_points": track["points"],
        **context,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--start", type=int, default=1650)
    parser.add_argument("--end", type=int, default=2760)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists")
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    digest = file_sha256(args.video)
    if (
        digest == reserved["source_sha256"]
        or args.video.resolve() == (ROOT / "validation/unseen-end/source.mp4").resolve()
        or any(args.source_id in row["video_url"] for row in reserved["reserved_rows"])
    ):
        parser.error("This source is reserved")
    cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    fps = cap.get(cv2.CAP_PROP_FPS)
    duration = cap.get(cv2.CAP_PROP_FRAME_COUNT) / fps if fps > 0 else 0
    if not 0 <= args.start < args.end <= duration:
        raise ValueError("Invalid interval or unreadable video")
    tracker = ScoreboardEvents()
    for t in range(args.start, args.end):
        cap.set(cv2.CAP_PROP_POS_FRAMES, round(t * fps))
        ok, frame = cap.read()
        if not ok:
            raise RuntimeError(f"Decode failed at {t} seconds")
        tracker.update(read_beijing_counts(frame), float(t))
    cap.release()
    anchors = []
    for row in tracker.unresolved:
        if row["kind"] == "counter_reset_or_inconsistent" and sum(row["before"]) == 1:
            anchors.append((row["time_interval_s"][0], row["before"]))
    if tracker.state is not None and sum(tracker.state.counts) == 1:
        anchors.append((tracker.state.last_seen_s, tracker.state.counts))
    fallback = []
    visual_events = []
    gap_rows = [
        row
        for row in tracker.unresolved
        if row["kind"] == "multi_throw_or_long_graphic_gap"
        and single_decrement(row["before"], row["after"])
    ]
    if anchors or gap_rows or tracker.state is not None:
        cap = cv2.VideoCapture(str(args.video), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
        for anchor_s, counts in anchors:
            colour = "red" if counts[0] == 1 else "yellow"
            evidence = verify_final_stone_motion(
                cap, fps, colour=colour, anchor_s=anchor_s, source_end_s=args.end
            )
            fallback.append(
                dict(evidence, anchor_s=anchor_s, remaining_counts=counts, colour=colour)
            )
            event = visual_event(
                evidence, colour, "visually_tracked_final_stone_motion", remaining_before=counts
            )
            if event:
                visual_events.append(event)
        for row in gap_rows:
            colour = single_decrement(row["before"], row["after"])
            before_s, after_s = row["time_interval_s"]
            evidence = verify_stone_motion_in_interval(
                cap,
                fps,
                colour=colour,
                start_s=max(args.start, before_s - 5),
                end_s=min(args.end, after_s + 2),
            )
            fallback.append(dict(evidence, reason="single_decrement_graphic_gap", counter_gap=row))
            event = visual_event(
                evidence, colour, "visually_tracked_single_decrement_gap", counter_gap=row
            )
            if event:
                visual_events.append(event)
        # Offline lookahead can corroborate motion already inside the requested interval.
        # A late counter update is evidence for colour, never a post-boundary event.
        if tracker.state is not None and sum(tracker.state.counts) > 1:
            before = tracker.state.counts
            for t in range(args.end, min(int(duration), args.end + 41)):
                cap.set(cv2.CAP_PROP_POS_FRAMES, round(t * fps))
                ok, frame = cap.read()
                if not ok:
                    break
                after = read_beijing_counts(frame)
                colour = single_decrement(before, after) if after is not None else None
                if colour is None:
                    continue
                evidence = verify_stone_motion_in_interval(
                    cap,
                    fps,
                    colour=colour,
                    start_s=max(args.start, args.end - 30),
                    end_s=args.end,
                )
                fallback.append(
                    dict(
                        evidence,
                        reason="post_boundary_counter_confirmation",
                        counter_before=before,
                        counter_after=after,
                        counter_confirmation_s=t,
                    )
                )
                event = visual_event(
                    evidence,
                    colour,
                    "visually_tracked_boundary_throw",
                    counter_before=before,
                    counter_after=after,
                    counter_confirmation_s=t,
                )
                if event:
                    visual_events.append(event)
                break
        cap.release()
    for index, event in enumerate(visual_events, 1):
        event["id"] = f"V{index:02}"
    events = sorted(tracker.events + visual_events, key=lambda e: e["crossing_time_s"])
    result = {
        "status": "development_beijing_overlay_visual_gap_and_boundary",
        "source_id": args.source_id,
        "source_sha256": digest,
        "source_interval_s": [args.start, args.end],
        "model_sha256": file_sha256(ROOT / "prototype/broadcast_scoreboard.py"),
        "visual_model_sha256": file_sha256(ROOT / "prototype/stone_motion_fallback.py"),
        "runner_sha256": file_sha256(__file__),
        "events": events,
        "scoreboard_events": tracker.events,
        "visual_fallback_events": visual_events,
        "visual_fallback_evidence": fallback,
        "unresolved": tracker.unresolved,
        "terminal_counter_state": asdict(tracker.state) if tracker.state else None,
        "samples": tracker.observations,
        "visible_samples": tracker.visible_samples,
        "limitations": [
            "Beijing 2022 graphic and 640x360 layout only; unsupported overlays return unknown.",
            "A graphic update confirms one remaining-stone decrement, not release time or stone trajectory.",
            "Multi-decrement and visually ambiguous graphic gaps remain unresolved.",
            "This adapter was developed after viewing the Canada–China 2022 recording.",
            "Visual recovery of long single-decrement gaps and boundary throws was developed after the Sweden–Switzerland first score.",
            "Boundary corroboration may use up to 40 seconds of later video; emitted motion must occur inside the requested interval.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                "events": len(events),
                "counter_events": len(tracker.events),
                "visual_events": len(visual_events),
                "unresolved": len(tracker.unresolved),
                "visible_samples": tracker.visible_samples,
            }
        )
    )


if __name__ == "__main__":
    main()
