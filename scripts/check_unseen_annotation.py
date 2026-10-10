"""Exercise blind annotation using synthetic video; never inspect reserved footage."""

import json
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix="curling-annotation-check-") as temporary:
    folder = Path(temporary)
    video = folder / "synthetic.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=640x360:rate=10",
            "-t",
            "12",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(video),
        ],
        check=True,
    )
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=os.environ.get("CHROMIUM_EXECUTABLE")
            or shutil.which("chromium")
            or shutil.which("chromium-browser"),
            args=["--no-sandbox"],
        )
        context = browser.new_context(viewport={"width": 1200, "height": 900})
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto((ROOT / "validation/unseen-end/annotate.html").as_uri())
        page.locator("#file").set_input_files(video)
        page.wait_for_function('document.querySelector("#video").readyState>=2')
        page.locator("#reviewer").fill("Synthetic browser test")
        page.locator("#blind").check()
        page.locator("#endstart").click()
        page.locator("#throwstart").click()

        def seek(t):
            page.locator("#seek").fill(str(t))
            page.locator("#go").click()
            page.wait_for_function(
                '(t)=>!document.querySelector("#video").seeking && Math.abs(document.querySelector("#video").currentTime-t)<.01',
                arg=t,
            )

        seek(1)
        page.locator("#throwfinish").click()
        seek(2)
        page.locator("#capture").click()
        page.locator("#canvas").click(position={"x": 150, "y": 100})
        page.locator("#boardnotes").fill("Synthetic pending-board restore check")
        page.locator("#boardnotes").blur()
        page.reload()
        page.locator("#file").set_input_files(video)
        page.locator("#canvas").wait_for(state="visible")
        assert page.locator("#boardnotes").input_value() == "Synthetic pending-board restore check"
        assert page.evaluate("board.stones.length") == 1
        page.locator("#complete").check()
        page.locator("#saveboard").click()
        seek(3)
        page.locator("#endfinish").click()
        with page.expect_download() as downloaded:
            page.locator("#export").click()
        path = folder / "reference-draft.json"
        downloaded.value.save_as(path)
        ref = json.loads(path.read_text())
        assert ref["independent"] and len(ref["events"]) == 1 and len(ref["boards"]) == 1
        assert len(ref["boards"][0]["stones"]) == 1 and ref["boards"][0]["complete"]
        assert ref["boards"][0]["time_s"] == 2
        page.locator("#import").set_input_files(path)
        page.wait_for_function(
            'document.querySelector("#status").textContent.startsWith("Draft imported")'
        )
        assert json.loads(page.locator("#json").input_value()) == ref
        page.reload()
        assert json.loads(page.locator("#json").input_value()) == ref
        assert "restored" in page.locator("#saved").inner_text()
        # Unsaved JSON changes cannot be silently lost by an annotation action.
        page.get_by_text("Advanced: edit reference JSON", exact=True).click()
        page.locator("#json").fill(page.locator("#json").input_value() + " ")
        page.locator("#endstart").click()
        assert "Apply or export" in page.locator("#status").inner_text()
        page.locator("#apply").click()
        # Practice is a separate draft and never loads test annotations.
        practice = page.context.new_page()
        practice.goto((ROOT / "validation/unseen-end/annotate.html").as_uri() + "?practice=1")
        draft = json.loads(practice.locator("#json").input_value())
        assert draft["purpose"] == "practice_only" and not draft["events"]
        assert draft["source_id"] == "aWXo6XeUFQw"
        assert practice.locator("#answers").inner_text() == ""
        practice.locator("#reveal").click()
        assert "1737" in practice.locator("#answers").inner_text()
        practice.locator("#load").click()
        practice.wait_for_function('document.querySelector("#video").readyState>=2')
        practice.locator("#practice-jump").click()
        practice.wait_for_function('Math.abs(document.querySelector("#video").currentTime-1720)<.1')
        practice.close()
        # Consecutive throws: an unfinished first board must not block or rewind capture.
        second_context = browser.new_context()
        two = second_context.new_page()
        two.on("pageerror", lambda e: errors.append(str(e)))
        two.goto((ROOT / "validation/unseen-end/annotate.html").as_uri())
        two.locator("#file").set_input_files(video)
        two.wait_for_function('document.querySelector("#video").readyState>=2')

        def seek_two(t):
            two.locator("#seek").fill(str(t))
            two.locator("#go").click()
            two.wait_for_function("(t)=>!v.seeking && Math.abs(v.currentTime-t)<.01", arg=t)

        two.locator("#throwstart").click()
        seek_two(1)
        two.locator("#throwfinish").click()
        seek_two(2)
        two.locator("#capture").click()
        two.locator("#canvas").click(position={"x": 140, "y": 100})
        first_image = two.locator("#canvas").evaluate("c=>c.toDataURL()")
        two.locator("#boardnotes").fill("Keep first throw annotations")
        seek_two(4)
        two.locator("#throwstart").click()
        seek_two(5)
        two.locator("#throwfinish").click()
        assert two.evaluate("data.boards[0].stones.length") == 1
        assert two.evaluate("data.boards[0].notes") == "Keep first throw annotations"
        seek_two(8)
        two.locator("#capture").click()
        assert two.evaluate("board.throw_id") == "E02"
        assert two.evaluate("board.time_s") == 8
        assert two.evaluate("board.stones.length") == 0
        assert two.locator("#canvas").evaluate("c=>c.toDataURL()") != first_image
        two.locator("#canvas").click(position={"x": 180, "y": 120})
        # A later loadeddata notification must not seek to the captured board.
        seek_two(9)
        two.evaluate("v.dispatchEvent(new Event('loadeddata'))")
        assert two.evaluate("v.currentTime") == 9
        # Also handle a draft from the old UI: selected throw differs from pending board.
        two.locator("#throwid").fill("E01")
        two.locator("#capture").click()
        assert two.evaluate("board.throw_id") == "E01"
        assert two.evaluate("board.time_s") == 9
        assert two.evaluate("data.boards.find(b=>b.throw_id==='E02').stones.length") == 1
        second_context.close()
        page.set_viewport_size({"width": 390, "height": 844})
        assert page.evaluate("document.documentElement.scrollWidth<=innerWidth"), "Mobile overflow"
        assert not errors, errors
        browser.close()
    print(
        "PASS: synthetic video, intervals, board clicks, export/import, dirty-draft guard, consecutive throws preserve marks and capture new frames, mobile layout; no held-out footage inspected"
    )
