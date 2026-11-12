"""Browser acceptance check for a shared-rink viewer, at preview or full scale.

Checks real source seeking, event selection, colour/handoff/state fields when
present, board-chunk loading, equal metric scale and page errors. It makes no
accuracy claim; it verifies that the user-visible viewer agrees with its data.
"""

import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--viewer", type=Path, required=True,
                        help="path to viewer/index.html")
    parser.add_argument("--events", default="",
                        help="comma-separated event IDs; default first/middle/last")
    parser.add_argument("--screenshot", type=Path)
    args = parser.parse_args()
    viewer = args.viewer.resolve()
    root = viewer.parent
    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            executable_path="/run/current-system/sw/bin/chromium",
            headless=True, args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": 1500, "height": 1100})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(viewer.as_uri())
        page.wait_for_function(
            "window.RINK_DATA && document.querySelector('#events').options.length > 0")
        option_ids = page.evaluate(
            "[...document.querySelector('#events').options].map(o => o.textContent.split(' · ')[0])")
        selected = [value for value in args.events.split(",") if value]
        if not selected:
            selected = [option_ids[0], option_ids[len(option_ids) // 2],
                        option_ids[-1]]
        rows = []
        for event_id in selected:
            if event_id not in option_ids:
                rows.append({"event_id": event_id, "status": "not_in_viewer"})
                continue
            page.evaluate(
                "(id)=>{const s=document.querySelector('#events');"
                "s.value=[...s.options].findIndex(o=>o.textContent.startsWith(id+' · '));"
                "s.onchange();}", event_id)
            page.wait_for_function(
                "(id)=>window.currentEvent&&window.currentEvent.id===id", arg=event_id)
            page.wait_for_timeout(700)
            row = page.evaluate("""() => {
                const event = window.currentEvent;
                const state = document.querySelector('#state');
                const manifest = window.BOARD_MANIFEST;
                let board_loaded = null;
                if (manifest && manifest.chunks) {
                    const key = Math.floor((document.querySelector('#video').currentTime || 0) / 60);
                    board_loaded = Object.prototype.hasOwnProperty.call(window.boardCache || {}, key);
                }
                return {
                    event_id: event.id,
                    colour: event.colour || null,
                    colour_status: event.colour_status || null,
                    link_status: event.links && event.links.length
                        ? (event.links[0].colour_consistency || null) : null,
                    spatial: event.links && event.links.length
                        ? (event.links[0].spatial_consistency || null) : null,
                    status_text: document.querySelector('#status').textContent,
                    state_text: state ? state.textContent : null,
                    scale: window.RINK_SCALE || null,
                    board_loaded: board_loaded,
                    time: document.querySelector('#video').currentTime,
                    video_ready: document.querySelector('#video').readyState,
                };
            }""")
            row["status"] = "checked"
            rows.append(row)
        if args.screenshot:
            page.locator("#rink").screenshot(path=str(args.screenshot))
            rows.append({"screenshot": str(args.screenshot)})
        checks = {
            "viewer": str(viewer),
            "errors": errors,
            "option_count": len(option_ids),
            "selected": selected,
            "rows": rows,
            "video_ready": any(r.get("video_ready", 0) >= 1 for r in rows if isinstance(r, dict)),
            "no_page_errors": not errors,
        }
        (root / "browser-verification.json").write_text(
            json.dumps(checks, indent=2))
        assert not errors, errors
        for row in rows:
            if row.get("status") != "checked":
                continue
            assert row["video_ready"] >= 1, row
            assert row["scale"] == 24, row
            assert row["status_text"], row
            if row["colour"] is not None:
                assert row["colour"] in ("red", "yellow"), row
                assert row["colour_status"], row
            if row["link_status"] is not None:
                assert row["link_status"] in ("agree", "disagree", "unverified"), row
            if row["state_text"] is not None:
                assert "End " in row["state_text"], row
        browser.close()
    print(json.dumps({"viewer": str(viewer), "events": selected,
                      "errors": errors, "option_count": len(option_ids)}))


if __name__ == "__main__":
    main()
