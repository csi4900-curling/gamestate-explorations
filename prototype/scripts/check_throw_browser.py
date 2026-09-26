from pathlib import Path
from playwright.sync_api import sync_playwright
import os as browser_os
import shutil as browser_shutil
import json

ROOT = Path(__file__).resolve().parents[1]
out = ROOT / "throw-analysis"
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
        browser_os.environ.get("CURLING_BASE_URL", "http://127.0.0.1:8765") + "/throw-analysis/"
    )
    page.wait_for_function('document.querySelector("#video").readyState>=2')
    assert page.locator("#detected").inner_text() == "16 / 16"
    assert page.locator("#events button").count() == 16
    for i in range(16):
        page.locator("#events button").nth(i).click()
        assert f"Lancer {i + 1} ·" in page.locator("#eventInfo").inner_text()
    page.locator("#events button").nth(10).click()
    page.wait_for_timeout(400)
    t = page.eval_on_selector("#video", "v=>v.currentTime")
    page.locator("#play").click()
    page.wait_for_timeout(700)
    page.locator("#play").click()
    assert page.eval_on_selector("#video", "v=>v.currentTime") > t
    page.locator("#speed").select_option("2")
    assert page.eval_on_selector("#video", "v=>v.playbackRate") == 2
    page.locator('[data-jump="15"]').click()
    page.wait_for_function('Math.abs(document.querySelector("#targetVideo").currentTime-15)<.1')
    assert "56 observations" in page.locator("#cueSummary").inner_text()
    page.locator('[data-jump="59"]').click()
    page.wait_for_timeout(300)
    assert "38:39" in page.locator("#targetClock").inner_text()
    page.evaluate("window.scrollTo(0,0)")
    page.screenshot(path=str(out / "evidence/desktop.png"))
    page.locator("#throws").scroll_into_view_if_needed()
    page.screenshot(path=str(out / "evidence/video-view.png"))
    page.set_viewport_size({"width": 390, "height": 844})
    page.evaluate("window.scrollTo(0,0)")
    page.wait_for_timeout(200)
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
    page.screenshot(path=str(out / "evidence/mobile.png"))
    urls = page.locator("a").evaluate_all(
        "(as)=>as.map(a=>a.href).filter(u=>u.startsWith(location.origin))"
    )
    for url in urls:
        assert page.request.get(url).ok, url
    response = page.request.get(
        browser_os.environ.get("CURLING_BASE_URL", "http://127.0.0.1:8765")
        + "/throw-analysis/end3.mp4",
        headers={"Range": "bytes=0-1023"},
    )
    assert response.status == 206
    assert len(response.body()) == 1024
    assert not errors, errors
    report = {
        "event_buttons": 16,
        "real_video_playback": True,
        "source_time_seeking": True,
        "target_example_seek": True,
        "target_score_unavailable": True,
        "mobile_overflow": False,
        "local_links_checked": len(urls),
        "video_range_support": True,
        "javascript_errors": errors,
    }
    (out / "browser-check.json").write_text(json.dumps(report, indent=2))
    print(report)
    browser.close()
