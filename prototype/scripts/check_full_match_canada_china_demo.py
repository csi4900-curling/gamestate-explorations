"""Check the offline full-match demo and its evidence separation."""

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
DEMO = ROOT / "prototype/full-match-canada-china"
DATA = json.loads((DEMO / "results.json").read_text())

assert DATA["provisional_event_count"] == len(DATA["events"]) == 125
assert DATA["official_shot_count"] == len(DATA["official_post_shot_states"]) == 125
assert DATA["unique_release_cue_count"] == 33
assert DATA["cross_view_colour_agreement_count"] == 5
assert DATA["source_two_view_colour_revision_count"] == 2
assert DATA["event_evidence_tiers"] == {
    "counter_backed_provisional": 116,
    "two_view_release_without_counter": 5,
    "visual_window_only_unconfirmed": 4,
}
assert DATA["counterless_motion_probe_with_track_count"] == 7
assert DATA["partial_board_link_count"] == 30
assert DATA["full_scan_board_count"] == 28
assert DATA["prior_only_board_count"] == 2
assert DATA["first_full_scan_board_score"]["matched_stone_count"] == 106
assert DATA["first_full_scan_board_score"]["complete_board_match_count"] == 16
assert DATA["counter_aligned_reference_link_count"] == 114
assert DATA["simulation_ready_count"] == 0
assert all(not row["simulation_ready"] and row["physical_settle_time_s"] is None
           and row["continuous_trajectory"] is None for row in DATA["events"])
by_id = {row["id"]: row for row in DATA["events"]}
assert by_id["VISUAL-S529"]["colour"] == "yellow"
assert by_id["VISUAL-S593"]["colour"] == "yellow"
assert by_id["VISUAL-S593"]["colour_reconciliation"]["original_colour"] == "red"

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path="/run/current-system/sw/bin/chromium",
                                args=["--no-sandbox"])
    page = browser.new_page(viewport={"width": 1500, "height": 1050})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto((DEMO / "index.html").as_uri())
    page.wait_for_function("document.querySelector('video').readyState >= 2")
    assert page.locator(".event-item").count() == 125
    assert page.locator("#official-state option").count() == 125
    page.locator("#search").fill("B57")
    assert page.locator(".event-item").count() == 1
    page.locator(".event-item").first.click()
    assert "pierre(s) observée(s)" in page.locator("#video-board-status").inner_text()
    page.locator("#search").fill("TRAVEL-B02")
    page.locator(".event-item").first.click()
    assert "Aucun indice unique" in page.locator("#release-cue").inner_text()
    page.locator("#search").fill("VISUAL-S593")
    page.locator(".event-item").first.click()
    assert "jaune" in page.locator("#event-title").inner_text().lower()
    page.locator("#search").fill("VISUAL-S52")
    page.locator(".event-item").first.click()
    assert "lancer non confirmé" in page.locator("#evidence-tier").inner_text().lower()
    assert "jaune" in page.locator("#motion-probe").inner_text().lower()
    page.locator("#search").fill("VISUAL-S403")
    page.locator(".event-item").first.click()
    assert "aucune piste" in page.locator("#motion-probe").inner_text().lower()
    page.locator("#official-next").click()
    assert page.locator("#official-state").input_value() != "0"
    page.set_viewport_size({"width": 390, "height": 844})
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    assert not errors, errors
    perspective = browser.new_page(viewport={"width": 1400, "height": 980})
    perspective.on("pageerror", lambda error: errors.append(str(error)))
    perspective.goto((DEMO / "rink-perspective.html").as_uri())
    assert perspective.locator("#state option").count() == 125
    assert "fin 7, lancer 16" in perspective.locator("#status").inner_text().lower()
    perspective.locator("#video-mode").click()
    assert perspective.locator("#state option").count() == 30
    assert "plateau partiel" in perspective.locator("#status").inner_text().lower()
    perspective.locator("#experimental-mode").click()
    assert perspective.locator("#state option").count() == 125
    b40 = perspective.evaluate("EXPERIMENTAL_VIDEO_STATES.rows.findIndex(row => row.counter_id === 'B40')")
    perspective.locator("#state").select_option(str(b40))
    assert "zone étendue : non" in perspective.locator("#status").inner_text().lower()
    b66 = perspective.evaluate("EXPERIMENTAL_VIDEO_STATES.rows.findIndex(row => row.counter_id === 'B66')")
    perspective.locator("#state").select_option(str(b66))
    assert "aucun plateau stable" in perspective.locator("#status").inner_text().lower()
    s593 = perspective.evaluate("EXPERIMENTAL_VIDEO_STATES.rows.findIndex(row => row.event_id === 'VISUAL-S593')")
    perspective.locator("#state").select_option(str(s593))
    assert "couleur corrigée par deux vues source" in perspective.locator("#status").inner_text().lower()
    s52 = perspective.evaluate("EXPERIMENTAL_VIDEO_STATES.rows.findIndex(row => row.event_id === 'VISUAL-S52')")
    perspective.locator("#state").select_option(str(s52))
    assert "lancer non confirmé" in perspective.locator("#status").inner_text().lower()
    perspective.locator("#wide-view").click()
    perspective.set_viewport_size({"width": 390, "height": 844})
    assert perspective.evaluate("document.documentElement.scrollWidth <= innerWidth")
    assert not errors, errors
    browser.close()

print("Full-match demo verified: 125 events, 125 official states, 30 frozen demo boards, 59 experimental video boards; no browser errors")
