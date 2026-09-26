"""One-to-one interval event evaluation, kept separate from inference."""

import json, hashlib
from pathlib import Path
import numpy as np
from scipy.optimize import linear_sum_assignment

ROOT = Path(__file__).resolve().parents[1]


def evaluate(events, reference, tolerance=2.0):
    n, m = len(reference), len(events)
    cost = np.full((n, m + n), 1e6)
    for i, r in enumerate(reference):
        lo, hi = r["crossing_interval_s"]
        for j, e in enumerate(events):
            d = max(lo - e["crossing_time_s"], 0, e["crossing_time_s"] - hi)
            if d <= tolerance:
                cost[i, j] = d
        cost[i, m:] = 1000
    pairs = []
    used = set()
    if n:
        ii, jj = linear_sum_assignment(cost)
        for i, j in zip(ii, jj):
            if j < m and cost[i, j] < 1000:
                used.add(int(j))
                pairs.append(
                    {
                        "reference_id": reference[i]["id"],
                        "prediction_id": events[j]["id"],
                        "reference_interval_s": reference[i]["crossing_interval_s"],
                        "predicted_crossing_s": events[j]["crossing_time_s"],
                        "distance_to_interval_s": float(cost[i, j]),
                        "colour_correct": events[j]["colour"] == reference[i]["colour"],
                    }
                )
    tp = len(pairs)
    matched = {p["reference_id"] for p in pairs}
    return {
        "reference_events": n,
        "predicted_events": m,
        "true_positives": tp,
        "false_positives": m - tp,
        "misses": n - tp,
        "precision": tp / m if m else None,
        "recall": tp / n if n else None,
        "predictions_inside_reference_interval": sum(
            p["distance_to_interval_s"] == 0 for p in pairs
        ),
        "colour_correct": sum(p["colour_correct"] for p in pairs),
        "pairs": pairs,
        "missed_ids": [r["id"] for r in reference if r["id"] not in matched],
        "false_prediction_ids": [events[j]["id"] for j in range(m) if j not in used],
    }


if __name__ == "__main__":
    out = ROOT / "throw-analysis"
    refpath = out / "reference.json"
    ref = json.loads(refpath.read_text())
    pred = json.loads((out / "predictions.json").read_text())
    assert (
        hashlib.sha256(refpath.read_bytes()).hexdigest()
        == (out / "reference.sha256").read_text().strip()
    ), "Frozen labels changed"
    assert pred["model_sha256"] == (out / "model-frozen.sha256").read_text().split()[0], (
        "Inference model differs from frozen version"
    )
    report = {
        "protocol": "One-to-one temporal association within labelled interval +2s; all unmatched detections counted. Colour is assessed after matching, not used to hide wrong-colour matches.",
        "timing_note": "References are coarse 1–2-second intervals. Zero interval distance is not zero timestamp error or measured release-time precision.",
        "reference_sha256": hashlib.sha256(refpath.read_bytes()).hexdigest(),
        "model_sha256": pred["model_sha256"],
        "all": evaluate(pred["events"], ref["events"]),
        "splits": {},
    }
    for name, (a, b) in ref["splits"].items():
        report["splits"][name] = evaluate(
            [e for e in pred["events"] if a <= e["crossing_time_s"] < b],
            [r for r in ref["events"] if r["split"] == name],
        )
    (out / "evaluation.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({k: v for k, v in report["all"].items() if k != "pairs"}, indent=2))
