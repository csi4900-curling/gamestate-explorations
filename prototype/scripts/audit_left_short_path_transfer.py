"""Verify unchanged short-path selection across other recordings."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256  # noqa: E402


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        p.error("Transfer audit already exists")
    manifest = json.loads(a.manifest.read_text())
    rows = []
    for item in manifest["recordings"]:
        base_path = ROOT / item["base_motion"]
        trial_path = ROOT / item["short_path_motion"]
        base, trial = json.loads(base_path.read_text()), json.loads(trial_path.read_text())
        if trial["base_motion_sha256"] != file_sha256(base_path):
            raise ValueError(f"Base motion hash differs for {item['recording']}")
        original = base["rows"]
        current = trial["rows"]
        if len(original) != len(current):
            raise ValueError(f"Candidate count differs for {item['recording']}")
        changed = []
        for old, new in zip(original, current):
            if (old["candidate_id"] != new["candidate_id"] or
                    old["receiving_view"] != new["receiving_view"]):
                raise ValueError(f"Candidate order differs for {item['recording']}")
            if old["selection"] != new["selection"]:
                changed.append(old["candidate_id"])
        row = {
            "recording": item["recording"],
            "base_motion_sha256": file_sha256(base_path),
            "short_path_motion_sha256": file_sha256(trial_path),
            "candidate_count": len(current),
            "left_candidate_count": sum(x["receiving_view"] == "left" for x in current),
            "changed_selection_ids": changed,
            "new_unique_short_path_ids": [d["candidate_id"]
                                          for d in trial["short_path_decisions"]
                                          if d["status"] == "unique_short_path_proposal"],
        }
        if "original_screen" in item:
            original_screen_path = ROOT / item["original_screen"]
            trial_screen_path = ROOT / item["short_path_screen"]
            old_screen = json.loads(original_screen_path.read_text())
            new_screen = json.loads(trial_screen_path.read_text())
            old_decisions = [(x["candidate_id"], x["status"], x["accepted"])
                             for x in old_screen["decisions"]]
            new_decisions = [(x["candidate_id"], x["status"], x["accepted"])
                             for x in new_screen["decisions"]]
            row["screen_decisions_identical"] = old_decisions == new_decisions
            row["accepted_count"] = len(new_screen["events"])
            row["original_screen_sha256"] = file_sha256(original_screen_path)
            row["short_path_screen_sha256"] = file_sha256(trial_screen_path)
            if not row["screen_decisions_identical"]:
                raise ValueError(f"Screen changed for {item['recording']}")
        rows.append(row)
    result = {
        "status": "cross_recording_development_short_path_selection_audit_not_event_accuracy",
        "manifest_sha256": file_sha256(a.manifest),
        "runner_sha256": file_sha256(Path(__file__)),
        "recording_count": len(rows),
        "left_candidate_count": sum(row["left_candidate_count"] for row in rows),
        "new_unique_short_path_count": sum(len(row["new_unique_short_path_ids"])
                                            for row in rows),
        "rows": rows,
        "limitations": [
            "These are existing 18.5-minute intervals, not full-match exhaustive labels.",
            "No changed selection means the rule had no observable path effect here; it does not prove safety on unseen cases.",
        ],
    }
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2) + "\n")
    print(result["recording_count"], "recordings;",
          result["left_candidate_count"], "left candidates;",
          result["new_unique_short_path_count"], "new paths")


if __name__ == "__main__":
    main()
