"""Audit v3 candidate order against official shot order using clean counter anchors."""

from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from prototype.official_candidate_sequence import align_official_sequence

BASE = ROOT / "validation/official-shot-sequence"
UNION = BASE / "pwg2022-provisional-event-evidence-union-v3-preorigin-travel-development.json"
COUNTERS = BASE / "pwg2022-official-counter-alignment.json"
REFERENCE = BASE / "pwg2022-official-shot-ledger.json"
OUTPUT = BASE / "pwg2022-v3-official-sequence-diagnostic-development.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def shot_number(event):
    return min(int(shot[1:]) for shot in event["source_shot_ids"])


def index(rows, key):
    result = {row[key]: row for row in rows}
    if len(result) != len(rows):
        raise ValueError(f"Duplicate {key}")
    return result


def build():
    union = json.loads(UNION.read_text())
    counters = json.loads(COUNTERS.read_text())
    reference = json.loads(REFERENCE.read_text())
    if counters["official_reference_sha256"] != digest(REFERENCE):
        raise ValueError("Official counter alignment differs from reference")
    counter_games = index(counters["games"], "official_game_code")
    reference_games = index(reference["games"], "official_game_code")
    reserved = json.loads((ROOT / "validation/unseen-end/reservation.json").read_text())
    games = []
    for game in union["games"]:
        code = game["official_game_code"]
        ref = reference_games[code]
        if (
            game["source_sha256"] != ref["source_video_sha256"]
            or game["source_sha256"] == reserved["source_sha256"]
        ):
            raise ValueError("Source mismatch or reserved-source overlap")
        counter_by_id = index(counter_games[code]["counter_rows"], "counter_id")
        events = sorted(game["events"], key=lambda e: (shot_number(e), e["event_id"]))
        anchors = []
        for event in events:
            counter_id = event["counter_id"]
            if counter_id is None:
                continue
            counter = counter_by_id[counter_id]
            if (
                counter["status"] == "unique_colour_concordant"
                and counter["official_shot_id"] is not None
                and event["colour"] == counter["official_colour"]
            ):
                anchors.append(
                    {
                        "event_id": event["event_id"],
                        "source_shot_number": shot_number(event),
                        "official_end": counter["official_end"],
                        "official_shot_number": counter["inferred_shot_number"],
                        "official_shot_id": counter["official_shot_id"],
                    }
                )
        if any(
            (right["official_end"], right["official_shot_number"])
            <= (left["official_end"], left["official_shot_number"])
            for left, right in zip(anchors, anchors[1:])
        ):
            raise ValueError("Clean counter anchors contradict source chronology")
        by_end = defaultdict(list)
        for anchor in anchors:
            by_end[anchor["official_end"]].append(anchor)
        ends = [row["end"] for row in ref["ends"]]
        if set(by_end) != set(ends):
            raise ValueError("Every official end needs a clean source anchor")
        boundaries = [
            (
                max(row["source_shot_number"] for row in by_end[left])
                + min(row["source_shot_number"] for row in by_end[right])
            )
            / 2
            for left, right in zip(ends, ends[1:])
        ]
        if any(right <= left for left, right in zip(boundaries, boundaries[1:])):
            raise ValueError("End midpoint boundaries overlap")
        grouped = defaultdict(list)
        for event in events:
            end = 1 + sum(shot_number(event) > boundary for boundary in boundaries)
            grouped[end].append(event)
        end_rows = []
        for official_end in ref["ends"]:
            end = official_end["end"]
            candidates = [
                {"candidate_id": event["event_id"], "colour": event["colour"]}
                for event in grouped[end]
            ]
            fixed = {row["event_id"]: row["official_shot_id"] for row in by_end[end]}
            if not set(fixed) <= {row["candidate_id"] for row in candidates}:
                raise ValueError("Counter anchor partitioned into wrong official end")
            result = align_official_sequence(
                candidates, official_end["shots"], ref["team_handle_colours"], fixed
            )
            end_rows.append(
                {
                    "end": end,
                    "candidate_count": len(candidates),
                    "official_shot_count": official_end["shot_count"],
                    "clean_fixed_counter_anchor_count": len(fixed),
                    "minimum_edit_cost": result["minimum_cost"],
                    "equally_optimal_alignment_count": result["optimal_path_count"],
                    "candidate_status_counts": dict(
                        Counter(row["status"] for row in result["candidate_rows"])
                    ),
                    "official_status_counts": dict(
                        Counter(row["status"] for row in result["official_rows"])
                    ),
                    "candidate_rows": result["candidate_rows"],
                    "official_rows": result["official_rows"],
                }
            )
        games.append(
            {
                "recording_code": code,
                "source_sha256": game["source_sha256"],
                "provisional_candidate_count": len(events),
                "official_shot_count": ref["official_shot_count"],
                "clean_fixed_counter_anchor_count": len(anchors),
                "end_partition_midpoint_shot_numbers": boundaries,
                "candidate_status_counts": dict(
                    Counter(row["status"] for end in end_rows for row in end["candidate_rows"])
                ),
                "official_status_counts": dict(
                    Counter(row["status"] for end in end_rows for row in end["official_rows"])
                ),
                "ends": end_rows,
            }
        )
    return {
        "status": "development_v3_official_order_sequence_audit_not_event_f1",
        "input_sha256": {
            "v3_union": digest(UNION),
            "counter_alignment": digest(COUNTERS),
            "official_reference": digest(REFERENCE),
            "alignment_code": digest(ROOT / "prototype/official_candidate_sequence.py"),
            "runner": digest(Path(__file__)),
        },
        "provisional_candidate_count": sum(g["provisional_candidate_count"] for g in games),
        "official_shot_count": sum(g["official_shot_count"] for g in games),
        "clean_fixed_counter_anchor_count": sum(
            g["clean_fixed_counter_anchor_count"] for g in games
        ),
        "candidate_status_counts": dict(
            Counter(
                row["status"]
                for game in games
                for end in game["ends"]
                for row in end["candidate_rows"]
            )
        ),
        "official_status_counts": dict(
            Counter(
                row["status"]
                for game in games
                for end in game["ends"]
                for row in end["official_rows"]
            )
        ),
        "games": games,
        "limitations": [
            "Official shot order and colour enter only this audit; this alignment is not a runtime video-only detector.",
            "Fixed counter anchors and end midpoint partitions are proxy assumptions, not physical throw identity.",
            "Every-optimum alignment statuses depend on the stated skip and colour costs and do not prove event precision or recall.",
            "Official shot pages provide no physical video timestamps, so event F1 remains unmeasured.",
        ],
    }


def main():
    payload = json.dumps(build(), indent=2) + "\n"
    if OUTPUT.exists() and OUTPUT.read_text() != payload:
        raise SystemExit("Existing v3 sequence audit differs from hashed inputs")
    if not OUTPUT.exists():
        OUTPUT.write_text(payload)
    print(f"Verified {OUTPUT}")


if __name__ == "__main__":
    main()
