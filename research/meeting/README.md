# Supervisor briefing — 26 September 2026

Open `../../supervisor-briefing.html` in a browser. The briefing embeds its illustration, experimental image, comparison data, styles and scripts, so the main document works offline. Links to project reports require the surrounding repository; research links require internet access.

- Seven short sections organised around the requests, work performed and resulting findings, approximately 7–9 minutes plus discussion. The briefing is in French and contains no em dashes.
- **Speaker notes** / **N** exposes a suggested narration.
- **Large type** / **L** increases reading size.
- **Print / PDF** includes notes. `../../supervisor-briefing.pdf` is a generated backup.
- The oblique comparison uses actual t100 data from `prototype/body-localization/results.json`.
- Current evidence, implemented components and proposals are explicitly distinguished.
- Resources from the previous reuse proposal are integrated, with primary links and robustness limitations. Selected primary pages rechecked 25 September 2026: CurlObserver, Curlovision, PCN, Opening the House, IFCD, PnLCalib, ByteTrack and Ultralytics.

Rebuild from the project root:

```sh
feasibility/scripts/python.sh research/meeting/build_briefing.py
feasibility/scripts/python.sh research/meeting/check_briefing.py
```

The second command uses the existing local Playwright environment and Chromium installation, checks interactions and local links, captures screenshots and regenerates the PDF. See `browser-check.json` for results. No experimental inference code or benchmark results were changed for this document.

Linked demo JSON is embedded by `embed_demo_data.py` during report builds. Open the root HTML directly; keep the project folders and videos alongside it. No localhost server is required for these report demos. The upload slideshow is excluded from the main presentation. External research links still require internet; the IFCD publisher returned HTTP 403 to automated checks. See `link-check.json`.
