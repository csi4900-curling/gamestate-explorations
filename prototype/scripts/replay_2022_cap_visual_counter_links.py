"""Attach delayed counters to existing cap-fusion visual events across cuts."""

from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from counter_shot_alignment import link_existing_visual_candidates
from shot_event_fusion import fuse_shot_events

BASE = ROOT / "validation/curlobserver-learned-probe"
INPUTS = {
    "PREL000101": ("swiss-full-transfer", "shot-origin.json", "two-shot-cap.json",
                   "cap-motion.json", "selected-learned-motion.json", "counter-cap.json",
                   "fused-cap.json"),
    "PREL000102": ("china-full-transfer", "unlabelled-shot-origin-inference.json",
                   "two-shot-cap.json", "sequential-shot-cap-motion.json",
                   "selected-shot-learned-motion.json",
                   "counter-shot-alignment-replay-cap.json",
                   "fused-shot-candidates-replay-cap.json"),
    "PREL000103": ("slovakia-full-transfer", "shot-origin.json", "two-shot-cap.json",
                   "cap-motion.json", "selected-learned-motion.json", "counter-cap.json",
                   "fused-cap.json"),
}
TRAVEL = ROOT / "validation/official-shot-sequence/pwg2022-cap-fusion-travel-rescue-development.json"
OUTPUT = ROOT / "validation/official-shot-sequence/pwg2022-cap-visual-counter-links-development.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def build():
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    travel = json.loads(TRAVEL.read_text())
    travel_by_game = {row["official_game_code"]: row for row in travel["games"]}
    games = []
    for code, names in INPUTS.items():
        folder, *files = names
        paths = [BASE / folder / filename for filename in files]
        origin, decision, cap, learned, alignment, fused = (
            json.loads(path.read_text()) for path in paths)
        source = fused["source_sha256"]
        if source == reserved["source_sha256"] or any(
                row["source_sha256"] != source for row in
                (origin, decision, cap, learned, alignment)):
            raise ValueError(f"Source mismatch or reserved source selected: {code}")
        if (fused["origins_sha256"] != digest(paths[0]) or
                fused["two_shot_sha256"] != digest(paths[1]) or
                fused["counter_alignment_sha256"] != digest(paths[4])):
            raise ValueError(f"Baseline fusion dependency mismatch: {code}")
        baseline = fuse_shot_events(origin["rows"], decision["decisions"],
                                    alignment["rows"], allow_rescue=False)
        if any(baseline[key] != fused[key] for key in
               ("events", "conflicts", "unassociated_counter_events")):
            raise ValueError(f"Baseline fusion did not reproduce: {code}")
        linked = link_existing_visual_candidates(
            alignment["rows"], origin["rows"], fused["events"],
            {"cap": cap["shots"], "learned": learned["shots"]})
        candidate = fuse_shot_events(origin["rows"], decision["decisions"],
                                      linked, allow_rescue=False)
        if len(candidate["events"]) != len(fused["events"]) or [
                row["shot_id"] for row in candidate["events"]] != [
                row["shot_id"] for row in fused["events"]]:
            raise ValueError(f"Existing candidate windows changed: {code}")
        added = [{"counter_id": new["counter_id"],
                  "counter_colour": new["colour"],
                  "shot_id": new["shot_id"],
                  "visual_colour_before": old_event["colour"],
                  "event_colour_after": new_event["colour"],
                  "colour_status_after": new_event["colour_status"],
                  "following_motion_options": new["existing_visual_candidates"]}
                 for old, new in zip(alignment["rows"], linked, strict=True)
                 if old["shot_id"] is None and new["shot_id"] is not None
                 for old_event, new_event in zip(fused["events"], candidate["events"], strict=True)
                 if old_event["shot_id"] == new["shot_id"] and
                 new_event["shot_id"] == new["shot_id"]]
        added_ids = {row["counter_id"] for row in added}
        travel_ids = {row["counter_id"] for row in travel_by_game[code]["rows"]
                      if row["status"] == "unlocalized_travel_candidate"}
        games.append({
            "official_game_code": code,
            "source_sha256": source,
            "input_sha256": dict(zip(("origins", "two_shot", "cap_motion",
                                       "learned_motion", "counter_alignment",
                                       "baseline_fusion"), map(digest, paths), strict=True)),
            "candidate_count_unchanged": len(candidate["events"]),
            "baseline_counter_linked_count": sum(
                row["counter_id"] is not None for row in fused["events"]),
            "new_counter_linked_count": sum(
                row["counter_id"] is not None for row in candidate["events"]),
            "new_link_count": len(added),
            "new_colour_conflict_count": len(candidate["conflicts"]),
            "unassociated_counter_count_after": len(candidate["unassociated_counter_events"]),
            "new_links_also_travel_proposals": len(added_ids & travel_ids),
            "new_links": added,
            "events": candidate["events"],
            "unassociated_counter_events": candidate["unassociated_counter_events"],
        })
    return {
        "status": "postscore_existing_event_counter_relink_not_physical_event_f1",
        "travel_audit_sha256": digest(TRAVEL),
        "link_code_sha256": digest(ROOT / "prototype/counter_shot_alignment.py"),
        "fusion_code_sha256": digest(ROOT / "prototype/shot_event_fusion.py"),
        "runner_sha256": digest(Path(__file__)),
        "games": games,
        "limitations": [
            "Counter matching uses selected learned-motion scans on exposed development sources.",
            "A same-colour following-view track does not prove the origin candidate is the same physical stone.",
            "Colour conflicts are preserved with null event colour; no candidate is deleted or added.",
            "No independent full-recording physical throw precision, recall or F1 is established.",
        ],
    }


def main():
    payload = json.dumps(build(), indent=2) + "\n"
    if OUTPUT.exists():
        if OUTPUT.read_text() != payload:
            raise SystemExit("Existing counter-link replay differs from current inputs or code")
        print(f"Verified {OUTPUT}")
    else:
        OUTPUT.write_text(payload)
        print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
