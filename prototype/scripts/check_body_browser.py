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
    page = browser.new_page(viewport={"width": 1440, "height": 1100})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(
        browser_os.environ.get("CURLING_BASE_URL", "http://127.0.0.1:8765") + "/body-localization/"
    )
    page.wait_for_function('document.querySelector("#detected").textContent==="46 / 48"')
    assert page.locator("#within").inner_text() == "40 / 48"
    assert page.locator("#median").inner_text() == "4.22 cm"
    assert page.locator("#misses").inner_text() == "2 / 0"
    assert page.locator("#frame option").count() == 11
    page.wait_for_timeout(400)
    before = page.locator("#board").screenshot()
    page.locator("#raw").uncheck()
    after = page.locator("#board").screenshot()
    assert before != after
    page.locator("#raw").check()
    page.locator("#frame").select_option("t136")
    assert "4/5 detected" in page.locator("#frameStatus").inner_text()
    assert "missed" in page.locator("#stones").inner_text()
    page.locator("#frame").select_option("t469")
    assert "diagnostic only" in page.locator("#frameStatus").inner_text()
    page.locator("#frame").select_option("t100")
    page.wait_for_function('document.querySelector("video").readyState>=2')
    page.locator("#play").click()
    page.wait_for_function("document.querySelector('#video').currentTime > 1")
    assert page.eval_on_selector("#video", "v=>v.currentTime") > 1
    page.locator("#play").click()
    page.locator("#jump").click()
    page.wait_for_function(
        "!document.querySelector('#video').seeking && document.querySelector('#clock').textContent.includes('sample 81/180')"
    )
    assert "sample 81/180" in page.locator("#clock").inner_text()
    baseline = page.locator("#videoBoard").screenshot()
    page.locator("#sensitivity").check()
    assert baseline != page.locator("#videoBoard").screenshot()
    page.locator("#showRawVideo").uncheck()
    assert "right camera" in page.locator("#videoStatus").inner_text()
    page.locator("#camera").select_option("left")
    assert "left camera" in page.locator("#videoStatus").inner_text()
    page.locator("#camera").select_option("right")
    page.locator("#showRawVideo").check()
    page.locator("#seek").evaluate("e=>{e.value='16';e.dispatchEvent(new Event('input'))}")
    page.wait_for_function(
        "!document.querySelector('#video').seeking && document.querySelector('#videoStatus').textContent.includes('geometry unavailable')"
    )
    assert "geometry unavailable" in page.locator("#videoStatus").inner_text()
    page.locator("#jump").click()
    page.wait_for_function(
        "!document.querySelector('#video').seeking && document.querySelector('#clock').textContent.includes('sample 81/180')"
    )
    page.screenshot(path="/tmp/curling-body-desktop.png", full_page=True)
    page.set_viewport_size({"width": 390, "height": 844})
    page.screenshot(path="/tmp/curling-body-mobile.png", full_page=True)
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
    for url in page.locator("a").evaluate_all(
        "(as)=>as.map(a=>a.href).filter(u=>u.startsWith(location.origin))"
    ):
        assert page.request.get(url).ok, url
    assert not errors, errors
    result = {
        "benchmark_counts": True,
        "all_frame_options": 11,
        "uncorrected_toggle_changes_pixels": True,
        "misses_and_exclusions_visible": True,
        "real_video_playback": True,
        "seeking_synchronized": True,
        "sensitivity_overlay": True,
        "both_cameras": True,
        "unavailable_geometry_emits_no_positions": True,
        "mobile_no_overflow": True,
        "local_links_ok": True,
        "javascript_errors": errors,
    }
    (ROOT / "body-localization/browser-check.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    browser.close()
