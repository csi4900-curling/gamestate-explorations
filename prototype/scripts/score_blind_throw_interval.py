"""Seal independent throw-only labels, then score a frozen event screen."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from blind_throw_scoring import score_throw_intervals  # noqa: E402
from cache_contract import file_sha256  # noqa: E402


def validate_labels(draft, packet):
    if (draft.get("schema") != "blind_throw_interval_v1" or
            draft.get("source_sha256") != packet["video_sha256"] or
            draft.get("source_offset_s") != packet["source_offset_s"] or
            draft.get("interval_local_s") != packet["interval_local_s"]):
        raise ValueError("Draft does not match the blind packet")
    if not draft.get("reviewer", "").strip() or draft.get("independent_confirmed") is not True:
        raise ValueError("Reviewer and independence declaration required")
    chunks = draft.get("reviewed_minutes")
    if (not isinstance(chunks, list) or len(chunks) != packet["chunk_count"] or
            any(value is not True for value in chunks)):
        raise ValueError("Every minute must be marked reviewed")
    offset = packet["source_offset_s"]
    local_start, local_end = packet["interval_local_s"]
    events = draft.get("events")
    if not isinstance(events, list):
        raise ValueError("Missing event list")
    ids = set()
    previous_end = None
    for event in sorted(events, key=lambda row: row["delivery_local_interval_s"][0]):
        event_id = event["id"]
        if event_id in ids:
            raise ValueError("Duplicate reference ID")
        ids.add(event_id)
        start, end = event["delivery_local_interval_s"]
        if (not local_start <= start < end <= local_end or
                (previous_end is not None and start <= previous_end) or
                event["delivery_source_interval_s"] != [start + offset, end + offset] or
                event["colour"] not in ("red", "yellow", "unknown") or
                type(event.get("uncertain")) is not bool or
                (event["uncertain"] and not event.get("notes", "").strip())):
            raise ValueError(f"Invalid delivery interval: {event_id}")
        previous_end = end


def seal(args):
    packet = json.loads(args.packet.read_text())
    draft = json.loads(args.draft.read_text())
    if file_sha256(args.video) != packet["video_sha256"]:
        raise ValueError("Blind video fingerprint differs")
    validate_labels(draft, packet)
    result = {
        "status": "sealed_human_throw_interval_reference_independence_declared",
        "packet_sha256": file_sha256(args.packet),
        "draft_sha256": file_sha256(args.draft),
        "video_sha256": packet["video_sha256"],
        "source_offset_s": packet["source_offset_s"],
        "interval_source_s": packet["interval_source_s"],
        "reference": draft,
        "seal_runner_sha256": file_sha256(Path(__file__)),
        "limitations": [
            "A declaration does not prove human independence or label accuracy.",
            "The reference covers throw intervals only, not stone boards or physical positions.",
        ],
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(len(draft["events"]), "reference intervals sealed")


def score(args):
    sealed = json.loads(args.seal.read_text())
    draft = json.loads(args.draft.read_text())
    packet = json.loads(args.packet.read_text())
    screen = json.loads(args.screen.read_text())
    alignment = json.loads(args.alignment.read_text())
    verification = json.loads(args.verification.read_text())
    if (sealed["status"] != "sealed_human_throw_interval_reference_independence_declared" or
            sealed["packet_sha256"] != file_sha256(args.packet) or
            sealed["draft_sha256"] != file_sha256(args.draft) or
            sealed["reference"] != draft or
            sealed["video_sha256"] != packet["video_sha256"] or
            alignment["interval_video_sha256"] != sealed["video_sha256"] or
            alignment["full_video_sha256"] != screen["source_sha256"] or
            alignment["source_offset_s"] != sealed["source_offset_s"] or
            alignment["all_best_at_zero_adjustment"] is not True or
            screen["source_interval_s"] != sealed["interval_source_s"] or
            verification["artifact_sha256"]["screen"] != file_sha256(args.screen) or
            verification["full_video_sha256"] != screen["source_sha256"] or
            verification["interval_video_sha256"] != sealed["video_sha256"]):
        raise ValueError("Sealed labels, alignment, or frozen screen differ")
    validate_labels(draft, packet)
    metrics = score_throw_intervals(draft["events"], screen["events"])
    result = {
        **metrics,
        "seal_sha256": file_sha256(args.seal),
        "draft_sha256": file_sha256(args.draft),
        "packet_sha256": file_sha256(args.packet),
        "screen_sha256": file_sha256(args.screen),
        "alignment_sha256": file_sha256(args.alignment),
        "verification_sha256": file_sha256(args.verification),
        "scoring_code_sha256": file_sha256(ROOT / "prototype/blind_throw_scoring.py"),
        "runner_sha256": file_sha256(Path(__file__)),
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(metrics["status"], metrics["f1"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    seal_parser = sub.add_parser("seal")
    for key in ("draft", "packet", "video", "output"):
        seal_parser.add_argument(f"--{key}", type=Path, required=True)
    score_parser = sub.add_parser("score")
    for key in ("seal", "draft", "packet", "screen", "alignment", "verification", "output"):
        score_parser.add_argument(f"--{key}", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve the first seal or score")
    if args.command == "seal":
        seal(args)
    else:
        score(args)


if __name__ == "__main__":
    main()
