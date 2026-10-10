"""Export review windows for the additive 358-candidate source-rescue union."""

from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.event_review_segments import build_review_segments

BASE = ROOT / "validation/official-shot-sequence"
UNION = BASE / "pwg2022-provisional-event-evidence-union-v2-source-rescues-development.json"
REFERENCE = BASE / "pwg2022-official-shot-ledger.json"
INPUTS = {
    "PREL000101": (ROOT / "validation/curlobserver-learned-probe/swiss-full-transfer/shot-review/manifest.json",
                   ROOT / "validation/curlobserver-learned-probe/swiss-full-transfer/possible-edits-v1.json"),
    "PREL000102": (ROOT / "validation/curlobserver-learned-probe/china-full-transfer/shot-review/manifest.json",
                   ROOT / "validation/curlobserver-learned-probe/china-full-transfer/possible-edits-v1.json"),
    "PREL000103": (ROOT / "validation/curlobserver-learned-probe/slovakia-full-transfer/shot-review/manifest.json",
                   ROOT / "validation/curlobserver-learned-probe/slovakia-full-transfer/possible-edits-v1.json"),
}
OUTPUT = BASE / "pwg2022-full-match-event-review-segments-v2-source-rescues-development.json"


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
            "source_only_rescue_review_count": sum(
                row["candidate_class"] == "source_only_two_view_release_provisional"
                for row in rows),
            "segments": rows,
        })
    return {"status": "development_v2_source_rescue_review_windows_not_physical_segments",
            "input_sha256": {"provisional_union_v2": digest(UNION),
                             "reference_metadata": digest(REFERENCE),
                             "segment_code": digest(ROOT / "prototype/event_review_segments.py"),
                             "runner": digest(Path(__file__))},
            "total_review_segment_count": sum(g["review_segment_count"] for g in games),
            "source_only_rescue_review_count": sum(
                g["source_only_rescue_review_count"] for g in games),
            "games": games,
            "limitations": [
                "Review windows include camera shots, not measured physical throw boundaries.",
                "The two new source-only candidates are provisional; physical identity and official shot assignment remain unverified.",
                "No complete-match independently labeled event F1 or simulation-ready state is established.",
            ]}


def main():
    payload = json.dumps(build(), indent=2) + "\n"
    if OUTPUT.exists() and OUTPUT.read_text() != payload:
        raise SystemExit("Existing v2 review export differs from hashed inputs")
    if not OUTPUT.exists():
        OUTPUT.write_text(payload)
    print(f"Verified {OUTPUT}")


if __name__ == "__main__":
    main()
