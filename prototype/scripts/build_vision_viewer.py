from pathlib import Path
import sys, json
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from vision_core import project

ROOT = Path(__file__).resolve().parents[1]
V = ROOT / "vision"
data = json.loads((V / "results.json").read_text())
data["evaluation"] = json.loads((V / "evaluation.json").read_text())
data["references"] = json.loads((V / "annotations/detection-reference.json").read_text())
cal = json.loads((V / "annotations/calibration.json").read_text())
for r in data["observations"]:
    r["region"] = cal["views"][r["panel"]]["region"]
    r["bounds"] = cal["views"][r["panel"]]["world_bounds"]
    r["rings"] = []
    if r["homography"] is not None:
        H = np.linalg.inv(r["homography"])
        a = np.linspace(0, 2 * np.pi, 120)
        for radius in [1.829, 1.219, 0.610]:
            r["rings"].append(project(H, np.c_[radius * np.cos(a), radius * np.sin(a)]).tolist())
text = (
    (ROOT / "vision-viewer.html")
    .read_text()
    .replace(
        "__DATA__",
        json.dumps(data, separators=(",", ":"))
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026"),
    )
)
(V / "index.html").write_text(text)
# Connect exact-timestamp experimental evidence to the full-video index without promoting its state.
p = ROOT / "runs/canada-korea/observations.json"
index = json.loads(p.read_text())
lookup = {(r["timestamp_s"], r["panel"]): r for r in data["observations"]}
index["vision_lab_url"] = "../../vision/index.html"
for o in index["observations"]:
    r = lookup.get((o["timestamp_s"], o["panel"]))
    if r:
        o["experimental_vision"] = {
            "url": f"../../vision/index.html#{r['timestamp_s']}-{r['panel']}",
            "candidate_count": len(r["candidates"]),
            "registration_status": r["registration"]["status"],
            "note": "Source-specific original-resolution cap proposals; not calibrated stone centres.",
        }
p.write_text(json.dumps(index, indent=2) + "\n")
from render import render

render(index, p.parent / "index.html")
print(
    "Built vision viewer and linked",
    sum("experimental_vision" in o for o in index["observations"]),
    "timeline observations",
)
