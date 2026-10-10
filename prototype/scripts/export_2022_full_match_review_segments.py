"""Export source-video review windows for all provisional 2022 events."""

from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from event_review_segments import build_review_segments

BASE = ROOT / "validation/official-shot-sequence"
UNION = BASE / "pwg2022-provisional-event-evidence-union-development.json"
REFERENCE = BASE / "pwg2022-official-shot-ledger.json"
INPUTS = {
    "PREL000101": (ROOT / "validation/curlobserver-learned-probe/swiss-full-transfer/shot-review/manifest.json",
                   ROOT / "validation/curlobserver-learned-probe/swiss-full-transfer/possible-edits-v1.json"),
    "PREL000102": (ROOT / "validation/curlobserver-learned-probe/china-full-transfer/shot-review/manifest.json",
                   ROOT / "validation/curlobserver-learned-probe/china-full-transfer/possible-edits-v1.json"),
    "PREL000103": (ROOT / "validation/curlobserver-learned-probe/slovakia-full-transfer/shot-review/manifest.json",
                   ROOT / "validation/curlobserver-learned-probe/slovakia-full-transfer/possible-edits-v1.json"),
}
OUTPUT = BASE / "pwg2022-full-match-event-review-segments-development.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def build():
    union = json.loads(UNION.read_text())
    reference = json.loads(REFERENCE.read_text())
    reference_by_code = {row["official_game_code"]: row for row in reference["games"]}
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    games = []
    for source in union["games"]:
        code = source["official_game_code"]
        manifest_path, edits_path = INPUTS[code]
        manifest, edits = (json.loads(path.read_text()) for path in
                           (manifest_path, edits_path))
        video = reference_by_code[code]
        if (source["source_sha256"] == reserved["source_sha256"] or
                any(row["source_sha256"] != source["source_sha256"]
                    for row in (manifest, edits)) or
                video["source_video_sha256"] != source["source_sha256"]):
            raise ValueError(f"Source mismatch or reserved source selected: {code}")
        rows = build_review_segments(source["events"], manifest["shots"],
                                     edits["possible_edits_outside_hard_cuts"])
        if len(rows) != source["provisional_event_count"]:
            raise ValueError(f"Event review coverage changed: {code}")
        games.append({
            "official_game_code": code,
            "source_sha256": source["source_sha256"],
            "source_video_path": video["source_video_path"],
            "source_interval_s": manifest["source_interval_s"],
            "input_sha256": {"shot_manifest": digest(manifest_path),
                             "possible_edits": digest(edits_path)},
            "review_segment_count": len(rows),
            "segments_with_possible_internal_edit": sum(
                bool(row["possible_internal_edit_times_s"]) for row in rows),
            "travel_only_segments_with_previous_shot": sum(
                row["unoccupied_previous_shot_added"] is not None for row in rows),
            "segments": rows,
        })
    return {
        "status": "full_source_provisional_event_review_windows_not_physical_throw_boundaries",
        "input_sha256": {"provisional_union": digest(UNION),
                         "reference_metadata": digest(REFERENCE),
                         "segment_code": digest(ROOT / "prototype/event_review_segments.py"),
                         "runner": digest(Path(__file__))},
        "games": games,
        "limitations": [
            "Each evidence core spans selected broadcast camera shots, not a measured physical throw.",
            "Review windows add context and may overlap; unknown release and settle times stay null.",
            "Possible internal edits are unverified camera-boundary proposals.",
            "The provisional event ledger has no independent complete-match physical throw F1.",
        ],
    }


def main():
    payload = json.dumps(build(), indent=2) + "\n"
    if OUTPUT.exists():
        if OUTPUT.read_text() != payload:
            raise SystemExit("Existing review segments differ from current inputs or code")
        print(f"Verified {OUTPUT}")
    else:
        OUTPUT.write_text(payload)
        print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
