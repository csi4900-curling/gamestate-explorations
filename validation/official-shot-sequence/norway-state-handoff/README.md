# Offline full-match evidence viewer

Open [index.html](index.html) in a browser. It works from `file://` because the frozen 128-shot [evidence handoff](../norway-full-match-evidence-state-handoff-first.json) is embedded at build time. Use Previous/Next, the shot selector, or left/right arrow keys. The checkbox filters to slots with a stable source-video house observation.

The left rink is the **official PDF schematic reference** after the selected shot. The right rink contains **partial observations from the broadcast camera shot**, in that image's house-relative coordinates. Their orientations are not automatically aligned. The event association, counter support, camera-shot ID, sampled interval, and any motion-direction proposal appear below the right rink. When a slot has multiple accepted camera-shot groups, use the camera selector.

The official reference can be stepped through for all 128 shots, but it is not a video reconstruction of the entire match. The video side has stable partial house observations at 47 slots. None of the slots has verified complete sheet state, exact release/settle time, measured revolution count, metric trajectory, or physical simulation readiness. Counterless S281→E04-S12 is shown as a proposal.

Regenerate after moving the frozen viewer outputs aside with `feasibility/scripts/python.sh prototype/scripts/render_norway_state_handoff_viewer.py`. [provenance.json](provenance.json) records the input, runner and generated HTML hashes. The viewer was opened in headless Chromium using `file://`; its embedded JavaScript passed `node --check`.
