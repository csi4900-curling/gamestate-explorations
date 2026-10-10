"""Browser smoke check for the local Latvia full-match evidence explorer."""

from hashlib import sha256
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
VIEWER = ROOT / "validation/throw-event-benchmark/canada-latvia-2024/full-match-review"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    errors = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path="/run/current-system/sw/bin/chromium", headless=True,
            args=["--allow-file-access-from-files", "--no-sandbox"])
        page = browser.new_page(viewport={"width": 1440, "height": 1050},
                                device_scale_factor=1)
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto((VIEWER / "index.html").as_uri())
        page.wait_for_selector(".candidate")
        assert page.locator(".candidate").count() == 127
        assert page.locator(".stat strong").all_text_contents() == [
            "127", "72", "47", "8"]
        page.locator("#filter").select_option("right_only_review_entry")
        assert page.locator(".candidate").count() == 8
        page.locator(".candidate").first.click()
        assert "right:R005" in page.locator("#selected-title").inner_text()
        assert page.locator("#video-overlay polyline").count() == 1
        assert page.locator("#board circle").count() == 4
        assert not page.locator("#post").is_disabled()
        assert "Simulation ready: no" in page.locator(".invariant").inner_text()
        page.locator("#video").evaluate("v => v.pause()")
        page.screenshot(path=str(VIEWER / "browser-r005.png"), full_page=True)
        page.locator("#filter").select_option("left_unconfirmed_raw_motion")
        assert page.locator(".candidate").count() == 47
        assert page.locator("#post").is_disabled()
        page.locator("#filter").select_option("left_provisional_passage")
        assert page.locator(".candidate").count() == 72
        page.locator("#filter").select_option("reviewed_person")
        assert page.locator(".candidate").count() == 3
        page.locator(".candidate").filter(has_text="left:R01-S45").click()
        assert "person at crossing" in page.locator("#motion-details").inner_text()
        assert "does not provide a stone passage" in page.locator("#state-note").inner_text()
        assert page.locator("#motion-details a").count() == 1
        assert not errors, errors
        browser.close()
    result = {"status": "local_browser_smoke_pass",
              "candidate_count": 127,
              "tier_counts": {"left_provisional_passage": 72,
                              "left_unconfirmed_raw_motion": 47,
                              "right_only_review_entry": 8},
              "right_r005_cap_proposal_count": 4,
              "source_reviewed_person_rows": 3,
              "page_errors": errors,
              "source_video_sha256": digest(VIEWER.parent / "source-360p.mp4"),
              "viewer_provenance_sha256": digest(VIEWER / "provenance.json"),
              "screenshot_sha256": digest(VIEWER / "browser-r005.png"),
              "runner_sha256": digest(Path(__file__))}
    (VIEWER / "browser-check.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"tiers": result["tier_counts"], "errors": errors}))


if __name__ == "__main__":
    main()
