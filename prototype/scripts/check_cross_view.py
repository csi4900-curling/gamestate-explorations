from pathlib import Path
import json, math
from playwright.sync_api import sync_playwright
import os as browser_os
import shutil as browser_shutil

ROOT = Path(__file__).resolve().parents[1]
out = ROOT / "cross-view"
data = json.loads((out / "results.json").read_text())
assert len(data["throws"]) == 16
for r in data["throws"]:
    if r["status"] == "provisional_link":
        assert (
            r["candidate_count"] == 1
            and r["gap"]["duration_s"] > 0
            and r["gap"]["longitudinal_distance_m"] > 0
        )
        assert not r["gap"]["interpolated"]
        assert (out / (r["id"] + "-evidence.jpg")).exists()
        for p in r["departure"] + r["arrival"]:
            assert all(math.isfinite(v) for v in p["world_m"])
with sync_playwright() as p:
    b = p.chromium.launch(
        executable_path=browser_os.environ.get("CHROMIUM_EXECUTABLE")
        or browser_shutil.which("chromium")
        or browser_shutil.which("chromium-browser"),
        args=["--no-sandbox"],
    )
    page = b.new_page(viewport={"width": 1400, "height": 1000})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto((out / "index.html").as_uri())
    page.wait_for_function('document.querySelector("video").readyState>=2')
    assert page.locator("#buttons button").count() == 16
    for i, r in enumerate(data["throws"]):
        page.locator("#buttons button").nth(i).click()
        page.wait_for_function(
            '(t)=>Math.abs(document.querySelector("video").currentTime-t)<.06',
            arg=(r["departure"][0]["time_s"] if r["departure"] else r["gate_time_s"]) - 1650,
        )
    page.locator("#buttons button").nth(7).click()
    page.locator("#arrival").click()
    page.wait_for_timeout(300)
    page.locator("#buttons button").nth(10).click()
    page.locator("#arrival").click()
    page.wait_for_function('document.querySelector("#gap").textContent.includes("0.61 m")')
    assert "29 observations" in page.locator("#coverage").inner_text()
    page.screenshot(path=str(out / "browser.png"), full_page=True)
    assert page.locator("#evidence details").count() == data["summary"]["provisional_links"]
    assert not errors, errors
    page.locator("video").evaluate("(v)=>{v.muted=true;return v.play()}")
    page.wait_for_timeout(300)
    assert not page.locator("video").evaluate("(v)=>v.paused")
    page.set_viewport_size({"width": 390, "height": 844})
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
    b.close()
result = {
    "offline_load": True,
    "video_playback": True,
    "all_16_buttons_seek": True,
    "javascript_errors": errors,
    "mobile_overflow": False,
    "gap_interpolation": False,
}
(out / "browser-check.json").write_text(json.dumps(result, indent=2))
print(result)
