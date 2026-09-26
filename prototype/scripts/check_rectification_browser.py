"""Run with the local Playwright environment and the workbench server on :8765."""

import json
from pathlib import Path
from playwright.sync_api import sync_playwright
import os as browser_os
import shutil as browser_shutil

ROOT = Path(__file__).resolve().parents[1]
with sync_playwright() as p:
    browser = p.chromium.launch(
        executable_path=browser_os.environ.get("CHROMIUM_EXECUTABLE")
        or browser_shutil.which("chromium")
        or browser_shutil.which("chromium-browser"),
        args=["--no-sandbox"],
    )
    page = browser.new_page(viewport={"width": 1400, "height": 1100})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(
        browser_os.environ.get("CURLING_BASE_URL", "http://127.0.0.1:8765") + "/rectification/"
    )
    page.wait_for_function(
        '!document.querySelector("#play").disabled && [...document.querySelectorAll("video")].every(v=>v.readyState>=2)'
    )
    assert page.locator("#leftMetric").inner_text() == "0.91 cm"
    assert page.locator("#rightMetric").inner_text() == "2.03 cm"
    dimensions = page.eval_on_selector(
        "#right", "v=>({width:v.videoWidth,height:v.videoHeight,duration:v.duration})"
    )
    assert dimensions == {"width": 588, "height": 588, "duration": 90}
    page.locator("#play").click()
    page.wait_for_timeout(1700)
    assert page.eval_on_selector("#master", "v=>v.currentTime") > 1
    drift = page.evaluate(
        'Math.abs(document.querySelector("#master").currentTime-document.querySelector("#right").currentTime)'
    )
    assert drift < 0.1, drift
    page.locator("#play").click()
    page.locator("#jump").click()
    page.wait_for_timeout(700)
    assert "40.00" in page.locator("#clock").inner_text()
    assert "frame 1201/" in page.locator("#clock").inner_text()
    with_guides = page.locator("#source").screenshot()
    page.locator("#guides").uncheck()
    without_guides = page.locator("#source").screenshot()
    assert with_guides != without_guides
    page.locator("#guides").check()
    page.locator("[name=referenceMode][value=before]").check()
    assert page.locator("#reference").get_attribute("src") == "right-before.jpg"
    page.locator("[name=referenceMode][value=after]").check()
    page.locator("#camera").select_option("left")
    page.wait_for_timeout(400)
    assert page.locator("#left").is_visible() and not page.locator("#right").is_visible()
    assert page.locator("#reference").get_attribute("src") == "left-after.jpg"
    page.locator("#camera").select_option("right")
    page.locator("#seek").evaluate("e=>{e.value='16';e.dispatchEvent(new Event('input'))}")
    page.wait_for_timeout(600)
    assert page.locator("#badge").inner_text() == "Calibration unavailable"
    page.locator("#jump").click()
    page.wait_for_timeout(400)
    page.screenshot(path="/tmp/curling-rectification-desktop.png", full_page=True)
    page.set_viewport_size({"width": 390, "height": 844})
    page.screenshot(path="/tmp/curling-rectification-mobile.png", full_page=True)
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
    assert not errors, errors
    links = page.locator("a").evaluate_all(
        "(as)=>as.map(a=>a.href).filter(h=>h.startsWith(location.origin))"
    )
    for url in links:
        assert page.request.get(url).ok, url
    result = {
        "actual_video_dimensions": dimensions,
        "playback_advances": True,
        "playback_drift_s": drift,
        "seek_frame_mapping": True,
        "guide_toggle_changes_pixels": True,
        "camera_switch": True,
        "before_after_reference_toggle": True,
        "unavailable_frame_16s_visible": True,
        "mobile_no_overflow": True,
        "local_links_ok": True,
        "javascript_errors": errors,
    }
    (ROOT / "rectification/browser-check.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    browser.close()
