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
        browser_os.environ.get("CURLING_BASE_URL", "http://127.0.0.1:8765") + "/stone-accuracy/"
    )
    page.wait_for_function('document.querySelector("#coverage").textContent==="4 / 48"')
    assert page.locator("#within").inner_text() == "0 / 48"
    assert page.locator("#position").inner_text() == "53.98 cm"
    assert page.locator(".tile").count() == 48
    assert page.locator(".tile.displaced").count() == 4
    assert page.locator("#frame option").count() == 11
    assert "4/4 visible targets detected" in page.locator("#frameResult").inner_text()
    page.wait_for_timeout(500)
    page.screenshot(path="/tmp/curling-stone-accuracy-desktop.png", full_page=True)
    page.locator("#frame").select_option("t136")
    page.wait_for_timeout(300)
    assert "0/5" in page.locator("#frameResult").inner_text()
    assert page.locator("#stones").inner_text().count("missed") == 5
    before = page.locator("#source").screenshot()
    page.locator("#showRejected").check()
    after = page.locator("#source").screenshot()
    assert before != after
    page.locator("#frame").select_option("t398")
    assert "diagnostic only" in page.locator("#frameResult").inner_text()
    page.locator("#frame").select_option("t469")
    assert "diagnostic only" in page.locator("#frameResult").inner_text()
    for option in page.locator("#frame option").evaluate_all("(os)=>os.map(o=>o.value)"):
        page.locator("#frame").select_option(option)
        for selector in ["#original", "#diagram"]:
            url = page.locator(selector).get_attribute("href")
            assert page.request.get(
                browser_os.environ.get("CURLING_BASE_URL", "http://127.0.0.1:8765")
                + "/stone-accuracy/"
                + url
            ).ok, url
    page.locator("#frame").select_option("t100")
    page.locator("#showRejected").uncheck()
    page.set_viewport_size({"width": 390, "height": 844})
    page.wait_for_timeout(300)
    page.screenshot(path="/tmp/curling-stone-accuracy-mobile.png", full_page=True)
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
    for url in page.locator("a").evaluate_all(
        "(as)=>as.map(a=>a.href).filter(h=>h.startsWith(location.origin))"
    ):
        assert page.request.get(url).ok, url
    assert not errors, errors
    result = {
        "headline_counts": True,
        "all_48_outcomes_visible": True,
        "11_frame_selections": True,
        "misses_are_not_zero_error": True,
        "rejection_overlay_changes_pixels": True,
        "diagnostic_exclusions_visible": True,
        "all_source_frames_and_diagrams_accessible": True,
        "mobile_no_overflow": True,
        "local_links_ok": True,
        "javascript_errors": errors,
    }
    (ROOT / "stone-accuracy/browser-check.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    browser.close()
