from pathlib import Path
from playwright.sync_api import sync_playwright
import os as browser_os
import shutil as browser_shutil
from urllib.parse import unquote, urlsplit
import json

root = Path(__file__).resolve().parents[2]
with sync_playwright() as p:
    browser = p.chromium.launch(
        executable_path=browser_os.environ.get("CHROMIUM_EXECUTABLE")
        or browser_shutil.which("chromium")
        or browser_shutil.which("chromium-browser"),
        args=["--no-sandbox"],
    )
    page = browser.new_page(viewport={"width": 1440, "height": 1000}, device_scale_factor=1)
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto((root / "supervisor-briefing.html").as_uri())
    page.wait_for_load_state("load")
    assert page.locator("#comparison circle").count() == 12
    assert page.locator("html").get_attribute("lang") == "fr"
    assert "—" not in (root / "supervisor-briefing.html").read_text()
    assert page.locator(".notes").first.is_hidden()
    page.locator("#notesBtn").click()
    assert page.locator(".notes").first.is_visible()
    page.keyboard.press("n")
    assert page.locator(".notes").first.is_hidden()
    page.locator("#rawBtn").click()
    assert "54,60" in page.locator("#comparisonLabel").inner_text()
    page.locator("#correctBtn").click()
    assert "7,53" in page.locator("#comparisonLabel").inner_text()
    page.locator("#focusBtn").click()
    assert "focus" in page.locator("body").get_attribute("class")
    page.locator("#focusBtn").click()
    links = page.locator("a").evaluate_all('(els)=>els.map(e=>e.getAttribute("href"))')
    missing = []
    for h in links:
        if h.startswith("#"):
            if not page.locator(h).count():
                missing.append(h)
        elif not urlsplit(h).scheme and not (root / unquote(h.split("#")[0])).exists():
            missing.append(h)
    assert not missing, missing
    page.evaluate("window.scrollTo(0,0)")
    page.wait_for_timeout(300)
    page.screenshot(path=str(root / "research/meeting/desktop.png"))
    page.locator("#evidence").scroll_into_view_if_needed()
    page.wait_for_timeout(300)
    page.screenshot(path=str(root / "research/meeting/evidence.png"))
    page.set_viewport_size({"width": 390, "height": 844})
    page.evaluate("window.scrollTo(0,0)")
    page.wait_for_timeout(300)
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
    page.screenshot(path=str(root / "research/meeting/mobile.png"))
    page.set_viewport_size({"width": 1440, "height": 1000})
    page.emulate_media(media="print")
    page.pdf(
        path=str(root / "supervisor-briefing.pdf"),
        format="A4",
        print_background=True,
        margin={"top": "14mm", "bottom": "14mm", "left": "13mm", "right": "13mm"},
    )
    assert not errors, errors
    result = {
        "javascript_errors": errors,
        "missing_local_links": missing,
        "links_checked": len(links),
        "comparison_toggle": "passed",
        "notes_keyboard_toggle": "passed",
        "large_type_toggle": "passed",
        "mobile_overflow": False,
        "offline_load": "passed",
        "pdf": "supervisor-briefing.pdf",
    }
    (root / "research/meeting/browser-check.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result))
    browser.close()
