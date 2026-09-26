"""Embed demo JSON so linked reports also work when opened via file://.
Run after rebuilding the demo HTML. Media files stay relative to the project.
"""

from pathlib import Path
import json, re

ROOT = Path(__file__).resolve().parents[2]
for relative, names in {
    "prototype/body-localization/index.html": [
        "results.json",
        "../stone-accuracy/results.json",
        "video-timeline.json",
        "transfer-check.json",
    ],
    "prototype/stone-accuracy/index.html": ["results.json"],
    "prototype/rectification/index.html": ["timeline.json", "calibration.json"],
    "prototype/continuous/index.html": ["timeline.json"],
}.items():
    p = ROOT / relative
    s = p.read_text()
    s = re.sub(r'<script id="embedded-demo-data">.*?</script>', "", s, flags=re.S)
    data = {n: json.loads((p.parent / n).read_text()) for n in names}
    script = (
        '<script id="embedded-demo-data">const embeddedDemoData='
        + json.dumps(data, separators=(",", ":")).replace("<", "\\u003c")
        + ";function reportJSON(url){return Object.hasOwn(embeddedDemoData,url)?Promise.resolve({ok:true,json:()=>Promise.resolve(embeddedDemoData[url])}):fetch(url);}</script>"
    )
    s = s.replace("fetch(", "reportJSON(")
    s = s.replace("<script>", script + "<script>", 1)
    p.write_text(s)
    print(relative)
