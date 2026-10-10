"""Run or resume the full-source shot/counter evidence pipeline without labels."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]


def file_sha256(path):
    digest = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stages(video, source_id, start, end, origin_model, learned_model, output,
           edit_audit=None):
    """Return ordered (artifact, module, arguments) stages."""
    path = lambda name: str(output / name)
    common = ["--video", str(video), "--source-id", source_id]
    span = ["--start", str(start), "--end", str(end)]
    origin = path("shot-origin.json")
    cap = path("cap-motion.json")
    learned = path("selected-learned-motion.json")
    counter = path("counter-replay.json")
    alignment_cap = path("counter-cap.json")
    alignment_two = path("counter-two-channel.json")
    alignment_rescue = path("counter-following-rescue.json")
    alignment_linked = path("counter-existing-visual-link.json")
    two_cap = path("two-shot-cap.json")
    two_both = path("two-shot-both.json")
    fused_cap = path("fused-cap.json")
    fused_both = path("fused-both.json")
    fused_rescue = path("fused-following-rescue.json")
    fused_linked = path("fused-linked.json")
    review = output / "shot-review"
    cuts = path("augmented-cuts.json") if edit_audit else path("hard-cuts.json")
    steps = [
        (output / "hard-cuts.json", "prototype.scripts.scan_scene_cuts",
         common + span + ["--output", path("hard-cuts.json")]),
        (output / "counter-audit.json", "prototype.scripts.audit_beijing_counter_full",
         common + span + ["--output", path("counter-audit.json")]),
        (output / "counter-replay.json", "prototype.scripts.replay_beijing_counter_audit",
         ["--audit", path("counter-audit.json"), "--output", counter]),
        (review / "manifest.json", "prototype.scripts.build_shot_review",
         ["--video", str(video), "--cuts", cuts,
          "--output", str(review)]),
        (output / "shot-origin.json", "prototype.scripts.evaluate_frozen_shot_origin_pair",
         ["--video", str(video), "--review", str(review),
          "--model", str(origin_model), "--output", origin]),
        (output / "cap-motion.json", "prototype.scripts.audit_full_shot_cap_motion",
         common + ["--review", str(review), "--output", cap]),
        (output / "counter-cap.json", "prototype.scripts.audit_counter_shot_alignment",
         ["--shot-score", origin, "--counter-audit", counter,
          "--motion-audit", cap, "--output", alignment_cap]),
        (output / "two-shot-cap.json", "prototype.scripts.confirm_shot_transitions",
         ["--origins", origin, "--cap-motion", cap, "--output", two_cap]),
        (output / "fused-cap.json", "prototype.scripts.fuse_shot_event_evidence",
         ["--origins", origin, "--two-shot", two_cap,
          "--counter-alignment", alignment_cap, "--output", fused_cap]),
        (output / "selected-learned-motion.json",
         "prototype.scripts.audit_selected_shot_learned_motion",
         ["--video", str(video), "--review", str(review), "--origins", origin,
          "--cap-decisions", two_cap, "--counter-alignment", alignment_cap,
          "--fused-events", fused_cap, "--model", str(learned_model),
          "--output", learned]),
        (output / "counter-two-channel.json",
         "prototype.scripts.audit_counter_shot_alignment",
         ["--shot-score", origin, "--counter-audit", counter,
          "--motion-audit", cap, "--motion-audit", learned,
          "--output", alignment_two]),
        (output / "counter-following-rescue.json",
         "prototype.scripts.audit_counter_shot_alignment",
         ["--shot-score", origin, "--counter-audit", counter,
          "--motion-audit", cap, "--motion-audit", learned,
          "--rescue-following-only", "--output", alignment_rescue]),
        (output / "two-shot-both.json", "prototype.scripts.confirm_shot_transitions",
         ["--origins", origin, "--cap-motion", cap,
          "--learned-motion", learned, "--output", two_both]),
        (output / "fused-both.json", "prototype.scripts.fuse_shot_event_evidence",
         ["--origins", origin, "--two-shot", two_both,
          "--counter-alignment", alignment_two, "--output", fused_both]),
        (output / "fused-following-rescue.json",
         "prototype.scripts.fuse_shot_event_evidence",
         ["--origins", origin, "--two-shot", two_both,
          "--counter-alignment", alignment_rescue, "--output", fused_rescue]),
        (output / "counter-existing-visual-link.json",
         "prototype.scripts.link_existing_counter_events",
         ["--origins", origin, "--alignment", alignment_rescue,
          "--cap-motion", cap, "--learned-motion", learned,
          "--fused-events", fused_rescue, "--output", alignment_linked]),
        (output / "fused-linked.json", "prototype.scripts.fuse_shot_event_evidence",
         ["--origins", origin, "--two-shot", two_both,
          "--counter-alignment", alignment_linked, "--output", fused_linked]),
        (output / "travel-only.json", "prototype.scripts.audit_counter_travel_fallback",
         ["--origins", origin, "--counter-alignment", alignment_linked,
          "--cap-motion", cap, "--learned-motion", learned,
          "--fused-events", fused_linked, "--output", path("travel-only.json")]),
        (output / "candidate-event-ledger.json",
         "prototype.scripts.build_throw_event_ledger",
         ["--fused-events", fused_linked, "--travel-only", path("travel-only.json"),
          "--counter-audit", counter, "--output", path("candidate-event-ledger.json")]),
    ]
    if edit_audit:
        steps.insert(1, (output / "augmented-cuts.json",
                         "prototype.scripts.augment_scene_cuts",
                         ["--hard-cuts", path("hard-cuts.json"),
                          "--edit-audit", str(edit_audit),
                          "--output", cuts]))
    return steps


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", required=True, type=Path)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--start", required=True, type=int)
    parser.add_argument("--end", required=True, type=int)
    parser.add_argument("--origin-model", required=True, type=Path)
    parser.add_argument("--learned-model", required=True, type=Path)
    parser.add_argument("--edit-audit", type=Path,
                        help="Development-only isolated edit proposals")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not 0 <= args.start < args.end:
        parser.error("Invalid source interval")
    for path in (args.video, args.origin_model, args.learned_model,
                 *([args.edit_audit] if args.edit_audit else [])):
        if not path.is_file():
            parser.error(f"Missing input: {path}")
    args.video = args.video.resolve()
    args.origin_model = args.origin_model.resolve()
    args.learned_model = args.learned_model.resolve()
    if args.edit_audit:
        args.edit_audit = args.edit_audit.resolve()
    args.output = args.output.resolve()
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    source_hash = file_sha256(args.video)
    if source_hash == reserved["source_sha256"]:
        parser.error("Reserved independent source cannot be used for development")
    for artifact, module, arguments in stages(
            args.video, args.source_id, args.start, args.end, args.origin_model,
            args.learned_model, args.output, args.edit_audit):
        command = [sys.executable, "-m", module, *arguments]
        if artifact.exists():
            existing = json.loads(artifact.read_text())
            runner = ROOT / (module.replace(".", "/") + ".py")
            if (existing.get("source_sha256") != source_hash or
                    existing.get("source_interval_s") != [args.start, args.end] or
                    existing.get("runner_sha256") != file_sha256(runner)):
                parser.error(f"Existing artifact has mismatched source, span or code: {artifact}")
            if (module == "prototype.scripts.augment_scene_cuts" and
                    existing.get("edit_audit_sha256") != file_sha256(args.edit_audit)):
                parser.error(f"Existing augmented cuts have mismatched edit audit: {artifact}")
        if args.dry_run:
            print(json.dumps({"artifact": str(artifact),
                              "state": "present" if artifact.exists() else "pending",
                              "command": command}))
        elif artifact.exists():
            print(f"SKIP {artifact}", flush=True)
        else:
            print(f"RUN {artifact}", flush=True)
            subprocess.run(command, cwd=ROOT, check=True)
    if not args.dry_run:
        print(f"Candidate ledger: {args.output / 'candidate-event-ledger.json'}")


if __name__ == "__main__":
    main()
