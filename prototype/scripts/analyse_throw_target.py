import sys, json, hashlib
from pathlib import Path
import cv2, numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from target_analysis import broom_candidates, stable_broom, receiving_outcome
from vision_core import project
from shot_intent import final_position_error

out = ROOT / "throw-analysis"
pred = json.loads((out / "predictions.json").read_text())
timeline = json.loads((ROOT / "body-localization/video-timeline.json").read_text())
rect = json.loads((ROOT / "rectification/timeline.json").read_text())
print("rect keys", rect.keys())
cap = cv2.VideoCapture(str(ROOT / "continuous/clip.mp4"))
fps = cap.get(cv2.CAP_PROP_FPS)
rows = []
n = 0
while cap.grab():
    if n % round(fps / 2) == 0:
        ok, frame = cap.retrieve()
        if not ok:
            raise ValueError("decode failure")
        candidates = broom_candidates(frame)
        rows.append({"time_s": n / fps, "source_time_s": 2260 + n / fps, "candidates": candidates})
    n += 1
cap.release()
# Use the frame-specific, accepted existing ice-plane calibration. No stone-height correction on a contact point.
for r in rows:
    rr = rect["records"][round(r["time_s"] * 30)]
    view = rr["views"]["right"]
    H = view.get("H")
    for c in r["candidates"]:
        c["position_m_if_ice_contact"] = (
            project(np.array(H), [c["pixel"]])[0].tolist() if H is not None else None
        )
examples = []
for event in pred["events"]:
    if not (2260 + 30 < event["crossing_time_s"] < 2350 - 35):
        continue
    cue = stable_broom(rows, event["crossing_time_s"])
    outcome = receiving_outcome(timeline, event)
    metric = final_position_error({"kind": cue.get("kind", "unknown")}, {})
    examples.append(
        {
            "event_id": event["id"],
            "crossing_time_s": event["crossing_time_s"],
            "broom_cue": cue,
            "outcome": outcome,
            "intended_destination": None,
            "shot_type": "unknown",
            "shot_accuracy": metric,
        }
    )
result = {
    "scope": "Existing 90-second original-resolution development clip; source-specific upright orange broom candidate. No automatic distinction between tactical pointing and aiming gesture.",
    "source_start_s": 2260,
    "samples": len(rows),
    "records": rows,
    "examples": examples,
    "primary_semantics_source": "https://curlingdescollines.ca/index.php/en/41-curling-info/300-different-shots-signals",
    "code_sha256": hashlib.sha256((ROOT / "target_analysis.py").read_bytes()).hexdigest(),
}
(out / "target-analysis.json").write_text(json.dumps(result, indent=2))
print(json.dumps(examples, indent=2)[:2500])
