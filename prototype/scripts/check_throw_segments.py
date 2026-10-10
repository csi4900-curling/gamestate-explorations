"""Check segment consistency and the offline review interface."""

from pathlib import Path
import json, math
from playwright.sync_api import sync_playwright
import os as browser_os
import shutil as browser_shutil

ROOT = Path(__file__).resolve().parents[1]
out = ROOT / "throw-segments"
data = json.loads((out / "results.json").read_text())
segments = data["segments"]
assert len(segments) == 16
for a, b in zip(segments, segments[1:]):
    assert a["end_s"] == b["start_s"]
assert segments[-1]["end_s"] == 2760
for s in segments:
    assert s["start_s"] < s["end_s"] and s["physical_end_s"] is None
    window = s["candidate_active_window"]
    assert window["start_s"] == s["observed_motion_start_s"] < s["start_s"]
    assert window["end_is_physical_stop"] is False
    assert s["physical_release_s"] is None
    if window["end_confirmation_s"] is not None:
        assert s["start_s"] < window["end_confirmation_s"] < s["end_s"]
        assert window["end_confirmation_s"] == s["delivered_stone_settling"]["time_s"]
    else:
        assert s["delivered_stone_settling"] is None
    assert s["visible_scene_stability_confirmation_s"] == s["settling"].get("confirmed_at_s")
    assert not s["pre_gate_path"]["straight_line_assumption_used"]
    if s["settling"].get("confirmed_at_s"):
        assert s["start_s"] < s["settling"]["confirmed_at_s"] < s["end_s"]
    for p in s["arrival_trajectory"]:
        if p["position_m"]:
            assert all(math.isfinite(v) for v in p["position_m"])
t12 = next(s for s in segments if s["id"] == "T12")
assert t12["visible_scene_stability_confirmation_s"] - t12["candidate_active_window"]["end_confirmation_s"] == 15.0
with sync_playwright() as p:
    b = p.chromium.launch(
        executable_path=browser_os.environ.get("CHROMIUM_EXECUTABLE")
        or browser_shutil.which("chromium")
        or browser_shutil.which("chromium-browser"),
        args=["--no-sandbox"],
    )
    page = b.new_page(viewport={"width": 1440, "height": 1000})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto((out / "index.html").as_uri())
    page.wait_for_function('document.querySelector("video").readyState>=2')
    assert page.locator("#buttons button").count() == 16
    for i, s in enumerate(segments):
        page.locator("#buttons button").nth(i).click()
        page.wait_for_function(
            '(expected)=>Math.abs(document.querySelector("video").currentTime-expected)<.05',
            arg=s["observed_motion_start_s"] - 1650,
        )
        page.locator("#start").click()
        page.wait_for_function(
            '(expected)=>Math.abs(document.querySelector("video").currentTime-expected)<.05',
            arg=s["start_s"] - 1650,
        )
        page.locator("#onset").click()
        page.wait_for_function(
            '(expected)=>Math.abs(document.querySelector("video").currentTime-expected)<.05',
            arg=s["observed_motion_start_s"] - 1650,
        )
    page.locator("#buttons button").nth(10).click()
    if not page.locator("#settled").is_disabled():
        page.locator("#settled").click()
    page.wait_for_timeout(250)
    page.screenshot(path=str(out / "browser.png"), full_page=True)
    # Test boundary stopping, using an actual selected interval rather than a timer mock.
    end = segments[10]["end_s"] - 1650
    page.locator("video").evaluate(
        "(v,t)=>{v.muted=true;v.currentTime=t;return v.play()}", end - 0.15
    )
    page.wait_for_timeout(650)
    assert page.locator("video").evaluate("(v)=>v.paused")
    assert abs(page.locator("video").evaluate("(v)=>v.currentTime") - end) < 0.06
    page.set_viewport_size({"width": 390, "height": 844})
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
    assert not errors, errors
    b.close()
result = {
    "segments": 16,
    "contiguous_review_boundaries": True,
    "all_buttons_seek": True,
    "boundary_auto_pause": True,
    "offline_video_load": True,
    "mobile_overflow": False,
    "javascript_errors": errors,
}
(out / "browser-check.json").write_text(json.dumps(result, indent=2))
print(result)
