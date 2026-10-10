"""Export an additive provisional event union with two source-only release rescues."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.source_release_rescue_union import append_source_release_rescues

BASE = ROOT / "validation/official-shot-sequence"
UNION = BASE / "pwg2022-provisional-event-evidence-union-development.json"
PROPOSALS = BASE / "pwg2022-outside-union-release-rescue-proposals-development.json"
RECEIVING = BASE / "pwg2022-outside-union-receiving-view-development.json"
MANIFESTS = {
    "PREL000101": ROOT / "validation/curlobserver-learned-probe/swiss-full-transfer/shot-review/manifest.json",
    "PREL000102": ROOT / "validation/curlobserver-learned-probe/china-full-transfer/shot-review/manifest.json",
    "PREL000103": ROOT / "validation/curlobserver-learned-probe/slovakia-full-transfer/shot-review/manifest.json",
}
OUTPUT = BASE / "pwg2022-provisional-event-evidence-union-v2-source-rescues-development.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def build():
    union = json.loads(UNION.read_text())
    proposals = json.loads(PROPOSALS.read_text())["proposals"]
    receiving = json.loads(RECEIVING.read_text())["rows"]
    if len(proposals) != 2 or len(receiving) != 2:
        raise ValueError("Expected two source-only rescue proposals")
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    games = []
    for game in union["games"]:
        code = game["official_game_code"]
        manifest = json.loads(MANIFESTS[code].read_text())
        if (game["source_sha256"] != manifest["source_sha256"]
                or game["source_sha256"] == reserved["source_sha256"]):
            raise ValueError("Source manifest mismatch or reserved-source overlap")
        local_proposals = [p for p in proposals if p["recording_code"] == code]
        local_receiving = []
        for row in receiving:
            if row["recording_code"] != code:
                continue
            proposal = next(p for p in local_proposals
                            if p["proposal_id"] == row["proposal_id"])
            if proposal["source_sha256"] != game["source_sha256"]:
                raise ValueError("Proposal source mismatch")
            track = row["tracks"][proposal["observed_colour"]]["strict"][0]
            matches = [shot for shot in manifest["shots"]
                       if shot["interval_s"][0] == row["cut_time_s"]
                       and shot["interval_s"][0] <= track["time_interval_s"][0]
                       and track["time_interval_s"][1] <= shot["interval_s"][1]]
            if len(matches) != 1:
                raise ValueError("Receiving track is not inside one camera shot")
            local_receiving.append({**row, "receiving_shot_id": matches[0]["id"]})
        events = append_source_release_rescues(game["events"], local_proposals,
                                               local_receiving)
        events.sort(key=lambda event: (
            min(int(shot[1:]) for shot in event["source_shot_ids"]),
            event["event_id"]))
        games.append({**{key: value for key, value in game.items()
                         if key not in ("events", "provisional_event_count",
                                        "candidate_class_counts")},
                      "provisional_event_count": len(events),
                      "source_only_rescue_count": len(local_proposals),
                      "candidate_class_counts": dict(sorted(Counter(
                          event["candidate_class"] for event in events).items())),
                      "events": events})
    return {"status": "development_provisional_event_union_v2_source_only_rescues_not_physical_f1",
            "input_sha256": {"frozen_union": digest(UNION),
                             "source_release_proposals": digest(PROPOSALS),
                             "receiving_view_audit": digest(RECEIVING),
                             "shot_manifests": {code: digest(path)
                                                for code, path in MANIFESTS.items()},
                             "merge_code": digest(ROOT / "prototype/source_release_rescue_union.py"),
                             "runner": digest(Path(__file__))},
            "total_provisional_event_count": sum(g["provisional_event_count"] for g in games),
            "source_only_rescue_count": sum(g["source_only_rescue_count"] for g in games),
            "games": games,
            "limitations": [
                "This additive v2 union preserves the frozen 356-event baseline separately; its two new rows are provisional source-only candidates.",
                "A unique same-colour receiving track after a verified cut does not establish persistent physical stone identity.",
                "No new counter or official-shot assignment, independently labeled F1, settled state transition, or simulation-ready trajectory is claimed.",
            ]}


def main():
    payload = json.dumps(build(), indent=2) + "\n"
    if OUTPUT.exists() and OUTPUT.read_text() != payload:
        raise SystemExit("Existing v2 union differs from hashed source evidence")
    if not OUTPUT.exists():
        OUTPUT.write_text(payload)
    print(f"Verified {OUTPUT}")


if __name__ == "__main__":
    main()
