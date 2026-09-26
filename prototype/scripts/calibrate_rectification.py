"""Fit reference ring geometry; keep the inner ring and angular samples out of fitting."""

import json, sys, cv2, numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from rectification_core import refine_calibration, rectify

cfg = json.loads((ROOT / "vision/annotations/calibration.json").read_text())
out = {}
folder = ROOT / "rectification"
folder.mkdir(exist_ok=True)
for name, view in cfg["views"].items():
    image = cv2.imread(str(ROOT / "vision/frames" / view["reference_frame"]))
    H, report = refine_calibration(image, view)
    out[name] = report
    for kind, mat in [("before", report["initial_H"]), ("after", H)]:
        frame, _ = rectify(image, np.array(mat), view["region"])
        cv2.imwrite(str(folder / f"{name}-{kind}.jpg"), frame)
    print(
        name,
        "inner radial RMSE before/after (m):",
        report["withheld_inner_before"]["radial_rmse_m"],
        report["withheld_inner_after"]["radial_rmse_m"],
    )
(folder / "calibration.json").write_text(json.dumps(out, indent=2))
