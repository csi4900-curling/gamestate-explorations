from pathlib import Path
import json, html
import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle

R = Path(__file__).resolve().parents[1]
O = R / "results"
s = json.loads((O / "summary.json").read_text())
a = json.loads((R / "annotations/manual.json").read_text())
m = pd.read_csv(O / "calibration_metrics.csv")
c = pd.read_csv(O / "stone_comparisons.csv")
plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "svg.fonttype": "none",
    }
)
fig, ax = plt.subplots(figsize=(11, 4.1), layout="constrained")
xx = np.arange(len(m))
ax.bar(xx - 0.18, m.check_rmse_cm, 0.36, label="Withheld ice landmarks", color="#197f9c")
ax.bar(xx + 0.18, m.house_rmse_cm, 0.36, label="Visible house stones vs. records", color="#d87d30")
ax.set_xticks(xx, m.frame)
ax.set_ylabel("RMSE (cm)")
ax.set_title(
    "Accurate painted geometry does not guarantee accurate stone positions",
    loc="left",
    fontweight="bold",
    pad=14,
)
ax.legend(frameon=False)
ax.grid(axis="y", alpha=0.17)
ax.set_axisbelow(True)
fig.savefig(O / "errors.svg")
fig.savefig(O / "errors.png", dpi=150)
plt.close(fig)
# Plot one clear overhead example in normalized official coordinates; arrows show measured discrepancy.
fig, ax = plt.subplots(figsize=(6, 6), layout="constrained")
for rad, col in [(1.829, "#d3edf0"), (1.219, "white"), (0.610, "#f9dddd")]:
    ax.add_patch(Circle((0, 0), rad, facecolor=col, edgecolor="#708494", lw=1))
ax.axhline(0, color="#adb8c2", lw=0.7)
ax.axvline(0, color="#adb8c2", lw=0.7)
for _, v in c[(c.frame == "t148") & c.matched].iterrows():
    color = "#be3f44" if v.colour == "R" else "#ae8d00"
    ax.plot(v.reference_x_m, v.reference_y_m, "o", color=color, ms=9, fillstyle="none", mew=1.5)
    ax.plot(v.pred_x_m, v.pred_y_m, "x", color=color, ms=7, mew=1.5)
    ax.plot([v.reference_x_m, v.pred_x_m], [v.reference_y_m, v.pred_y_m], color=color, lw=1)
ax.plot([], [], "o", color="#425260", fillstyle="none", label="CurlR reference")
ax.plot([], [], "x", color="#425260", label="Manually measured from video")
ax.legend(frameon=False, loc="lower left")
ax.set(
    xlim=(-2, 2),
    ylim=(-2, 2),
    aspect="equal",
    xlabel="Diagram-normalized x (m)",
    ylabel="Diagram-normalized y (m)",
)
ax.set_title("148 s · Eight visible house stones", loc="left", fontweight="bold")
ax.invert_yaxis()
fig.savefig(O / "board_comparison.svg")
fig.savefig(O / "board_comparison.png", dpi=150)
plt.close(fig)
fmt = lambda x: "—" if pd.isna(x) else f"{x:.2f}"
rows = "".join(
    f"<tr><td><a href='#f-{v.frame}'>{v.frame[1:]} s</a></td><td>{int(v.end)} / {int(v.shot)}</td><td>{v.model}</td><td>{int(v.fit_points)} / {int(v.check_points)}</td><td>{v.check_rmse_cm:.2f}</td><td>{int(v.house_matches)}</td><td>{fmt(v.house_rmse_cm)}</td><td>{int(v.unmatched_observations) if pd.notna(v.unmatched_observations) else '—'}</td></tr>"
    for _, v in m.iterrows()
)
cards = []
for f in a["frames"]:
    v = m[m.frame == f["id"]].iloc[0]
    cards.append(
        f"""<article class='frame' id='f-{f["id"]}'><h3>{f["timestamp_s"]} s · End {f["end"]} / reference shot {f["shot"]}</h3><p class='meta'>{v.model.upper()} · {f["pairing_status"].replace("_", " ")} · {v.fit_points} fitted / {v.check_points} withheld landmarks</p><a href='results/{f["id"]}_annotated.jpg'><img loading='lazy' src='results/{f["id"]}_annotated.jpg' alt='Annotated frame at {f["timestamp_s"]} seconds: fitted and withheld landmarks and manual stone centres'></a><p>{html.escape(f["notes"])}</p><p class='meta'>Withheld landmark RMSE {v.check_rmse_cm:.2f} cm. One-pixel calibration-click perturbations: 95th-percentile stone displacement {v.fit_click_sigma_1px_p95_cm:.2f} cm (includes guards where annotated).</p><p><a href='results/{f["id"]}_rectified.jpg'>Rectified view</a> · <a href='sources/official_shot_diagrams/end{f["end"]}_shot{f["shot"]}.png'>Original official diagram</a> · <a href='{f["original_image"]}'>Full-resolution source frame</a></p></article>"""
    )
o = s["overhead_house_reference_discrepancy_repeat_excluded"]
g = s["landmark_validation"]
z = s["repeat_zoom_consistency"]
report = f"""<!doctype html><html lang='en'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Curling calibration · feasibility pilot</title>
<style>:root{{--ink:#172535;--muted:#55677a;--blue:#197f9c}}*{{box-sizing:border-box}}html{{scroll-behavior:smooth}}body{{margin:0;background:#f3f6f8;color:var(--ink);font:16px/1.65 system-ui,sans-serif}}main{{max-width:1120px;margin:auto;padding:30px 24px 70px}}header{{background:#102d42;color:white;padding:48px 28px}}header>div{{max-width:1070px;margin:auto}}h1{{font-size:clamp(30px,5vw,48px);line-height:1.1;max-width:850px;margin:12px 0 20px;letter-spacing:-1.3px}}h2{{font-size:26px;margin-top:42px}}h3{{line-height:1.3}}p{{max-width:950px}}a{{color:#06627f;text-underline-offset:3px}}header a{{color:#b6e8ef}}.eyebrow{{text-transform:uppercase;letter-spacing:2px;font-size:12px}}.lead{{font-size:20px;max-width:870px}}.meta{{font-size:13px;color:var(--muted)}}.kpis{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:28px 0}}.kpi,.box,.frame{{background:white;border:1px solid #dbe4eb;border-radius:12px;padding:22px}}.kpi strong{{font-size:34px;display:block;color:var(--blue);line-height:1.3}}.kpi span{{font-size:13px;display:block}}.box{{border-left:5px solid var(--blue)}}.warn{{border-left-color:#ce8438;background:#fffaf3}}img{{max-width:100%;height:auto;display:block}}.chart{{background:white;padding:12px;border-radius:12px}}.table{{overflow:auto}}table{{width:100%;border-collapse:collapse;font-size:13px;background:white}}th,td{{padding:11px;text-align:left;border-bottom:1px solid #dce4eb;white-space:nowrap}}th{{background:#e8eff4}}.frames{{display:grid;grid-template-columns:1fr 1fr;gap:20px}}.frame{{padding:18px}}.frame h3{{margin:0 0 8px}}.frame p{{font-size:14px}}.split{{display:grid;grid-template-columns:1fr 1fr;gap:24px;align-items:center}}code{{background:#e5edf2;padding:2px 5px;border-radius:4px}}li{{margin:8px 0}}footer{{margin-top:45px;border-top:1px solid #cfdbe5;padding-top:20px}}@media(max-width:760px){{.kpis,.frames,.split{{grid-template-columns:1fr}}.kpis{{grid-template-columns:1fr 1fr}}main{{padding:20px 15px}}}}@media print{{header{{background:white;color:black;padding:10px}}.frame{{break-inside:avoid}}.frames{{display:block}}a{{color:inherit}}}}</style>
<header><div><div class='eyebrow'>Completed exploratory experiment · 23 September 2026</div><h1>Manual calibration works on selected overhead views.</h1><p class='lead'>The next bottleneck is reliable stone state and reference quality. A small geometric error alone is not an end-to-end green light.</p><p>Canada–Switzerland · 2018 Olympic mixed-doubles final · CBC edited highlights</p></div></header><main>
<div class='kpis'><div class='kpi'><strong>11</strong><span>manually annotated frames<br>9 homographies + 2 affine fallbacks</span></div><div class='kpi'><strong>{g["rmse_cm"]:.2f} cm</strong><span>withheld landmark RMSE<br>39 points, same annotator</span></div><div class='kpi'><strong>{o["median_cm"]:.2f} cm</strong><span>median overhead stone discrepancy<br>{o["n"]} matches; RMSE {o["rmse_cm"]:.2f} cm</span></div><div class='kpi'><strong>{z["rmse_cm"]:.2f} cm</strong><span>same-board zoom disagreement<br>7 paired stones, two frames</span></div></div>
<div class='box'><b>Decision: proceed with a constrained overhead-view pilot.</b><p>There is enough evidence to justify the next implementation step: manually verified overhead frames → stone centres → calibrated coordinates. Keep low-angle footage outside the accuracy claim until stone-height effects are handled. Treat official diagram positions as a noisy reference, and report coverage and refusals alongside position errors.</p></div>
<h2>What was actually done</h2><p>I sourced the <a href='https://www.youtube.com/watch?v=qqXEvKF-lM8'>CBC video</a>, downloaded the <a href='https://curlit.com/PDF/OWG2018_ResultsBook.pdf'>official Results Book</a>, loaded the pinned <a href='https://github.com/ritchi12/CurlR'>CurlR dataset</a>, and manually marked visible rink landmarks and stone body centres. The pilot covers 11 selected frames and 10 end/shot keys. One key is excluded from state comparison because the final collision is still settling; another observation repeats a board at a different zoom. There are <b>nine distinct reference states compared</b>, including two deliberately partial stationary-stone comparisons.</p><p>Each frame uses 6–8 fitting landmarks and 2–4 separate validation landmarks. Most fits use one set of ring/line intersections and validate on another ring. Radii are nominal <a href='https://worldcurling.org/wp-content/uploads/2025/08/Rules-2025.pdf'>World Curling dimensions</a>: 1.829, 1.219 and 0.610 metres. There was no stone-based adjustment of the calibration.</p>
<h2>The two error measurements answer different questions</h2><div class='chart'><img src='results/errors.svg' alt='Per-frame bar chart: independent ice landmark RMSE versus visible stone discrepancy against CurlR'></div><p class='meta'>The blue bars measure agreement with nominal painted geometry on withheld points. The orange bars combine video measurement, stone height, timing, identity matching and reference-diagram error. They cannot be interpreted as detector accuracy. The 398 s and 414 s views repeat one board; 469 s has no orange bar because its state was rejected.</p>
<div class='split'><div><h3>Overhead visible-stone comparison</h3><p>After excluding the duplicate close view from the headline aggregate, <b>44 matched house-stone observations across eight reference states</b> have a median discrepancy of <b>{o["median_cm"]:.2f} cm</b> and RMSE of <b>{o["rmse_cm"]:.2f} cm</b>. The largest is <b>{o["max_cm"]:.2f} cm</b>. Observations are correlated: a stationary stone may appear in more than one state.</p><p>Including the oblique view gives 48 house matches, median <b>{s["house_reference_discrepancy_repeat_excluded"]["median_cm"]:.2f} cm</b> and RMSE <b>{s["house_reference_discrepancy_repeat_excluded"]["rmse_cm"]:.2f} cm</b>. Its four house stones alone have 32.86 cm RMSE even though its ice-landmark RMSE is 4.01 cm.</p><p>One visible lateral stone at 194 s has no reference match within the fixed 50 cm gate. It remains explicitly unmatched; it is not included in position-error averages. This is a visible-subset comparison, not complete-board reconstruction or detection recall.</p></div><img src='results/board_comparison.svg' alt='Top-down comparison of eight manually measured stones and CurlR diagram positions at 148 seconds'></div>
<h2>Failures and controls that matter</h2><ul><li><b>Unidentifiable homographies:</b> at 398 s and 449 s, almost all available fitting landmarks lie on the tee line, with only one off-line point. More points did not fix the missing geometry. The unrestricted first run produced large held-out errors. The pipeline now rejects that configuration before fitting a homography. An affine fallback, appropriate as an exploratory approximation for these near-overhead views, gives held-out RMSE of 1.21 and 2.12 cm. Each has only two validation points, so the evidence is limited. <a href='results/initial_homography_attempt/calibration_metrics.csv'>Original failed run</a>.</li>
<li><b>Stone height / low-angle geometry:</b> a planar transform maps the ice, not the top of a stone. The oblique result is consistent with substantial height bias, but this pilot does not isolate that cause from reference error. No height correction was applied.</li>
<li><b>Motion audit:</b> adjacent <a href='frames/t230_960.png'>230 s</a> and <a href='frames/t232_960.png'>232 s</a> frames reveal yellow stones moving during end clearance. Those observations were removed from the 231 s comparison, while the two stationary reds were retained. At 309 s, the yellow shooter is moving; only stationary red stones are compared to the preceding official state. The final 469 s collision is calibration-only. Earlier comparisons remain in <a href='results/before_motion_audit/stone_comparisons.csv'>the audit archive</a>.</li>
<li><b>Repeat-zoom check:</b> all seven common house stones at 398/414 s match one-to-one. Their measured positions differ by median {z["median_cm"]:.2f} cm, RMSE {z["rmse_cm"]:.2f} cm, maximum {z["max_cm"]:.2f} cm. Repeatability is useful evidence but is not absolute accuracy.</li>
<li><b>Click sensitivity:</b> 500 seeded perturbations at both 1 and 2 review-image pixels quantify sensitivity to landmark placement. One pixel is two original-video pixels. The reported 95th percentiles describe this noise model only, not total uncertainty or confidence intervals. Distant guards and the low-angle view are more sensitive than central house stones.</li></ul>
<h2>Reference audit</h2><p>CurlR coordinates are <b>diagram pixels, not metres</b>; its stone indices are detection order, not delivery identities. I extracted the original 300 × 600 diagrams from PDF pages 1202–1207. In CurlR's normalized orientation, the tee is near (149.5, 159.5), and the outer ring has radius 120 pixels: one pixel corresponds to about <b>1.524 cm</b>. Raw diagrams alternate orientation, so direct use of an unnormalized image would flip the result.</p><p>Removed/unused stones in the top and bottom storage strips are excluded. Matching is by colour and one-to-one spatial assignment, with dummy unmatched options and a fixed 0.50 m gate. The reported house region is within 2.0 m of the tee. A repeated red stone in end 2 disagrees with the reference by about 20 cm in both video views; that needs a reference-position audit, not blind tuning of the calibration. Official book coordinates are not independently surveyed physical truth.</p>
<h2>Per-frame results</h2><div class='table'><table><thead><tr><th>Video time</th><th>End / shot</th><th>Model</th><th>Fit / check</th><th>Check RMSE cm</th><th>House matches</th><th>Record RMSE cm</th><th>Unmatched*</th></tr></thead><tbody>{rows}</tbody></table></div><p class='meta'>*Unmatched refers to annotated visible observations, including stones outside the house. Invisible reference stones are not counted as missed detections. 231/309 s are partial stationary-state comparisons. 398/414 s repeat the same state. 469 s is excluded from official-state metrics.</p>
<h2>Annotated evidence</h2><p>Green crosses were used to fit; cyan crosses were withheld. Click any image for its larger version. Rectified images are visual diagnostics, not a second validation set.</p><div class='frames'>{"".join(cards)}</div>
<h2>Limits on the conclusion</h2><div class='box warn'><p>This is a selected-view, single-match exploratory pilot. The same assistant annotated fitting and validation points; no independent human annotator or physical survey checked them. The affine model choice was made after the initial homography failure, and motion exclusions were made during inspection, so this is not a preregistered or blind test. The painted radii are nominal, residual lens distortion is unmodelled, and diagrams have quantization plus unknown placement error.</p><p>The experiment demonstrates a workable manual measurement path and exposes failure conditions. It does not establish general broadcast robustness, automatic detection quality, end-to-end game-state accuracy, full-board coverage or clinical/sport-science-grade measurement.</p></div>
<h2>Concrete next experiment</h2><p>Freeze the overhead-only acceptance rule, collect a new unexamined set of 20 shots from another match, and compare automatically detected stone centres against independently checked manual centres. Keep the calibration-basis rejection, explicit moving/occluded flags, and game-level separation. Report accepted-shot coverage and unmatched stones alongside error. Use manually audited video labels for the tight positional claim; keep CurlR agreement as a separate reference comparison.</p>
<footer><p><a href='README.md'>Reproduction instructions</a> · <a href='annotations/manual.json'>All manual annotations</a> · <a href='results/calibration_metrics.csv'>Calibration CSV</a> · <a href='results/stone_comparisons.csv'>Stone comparison CSV</a> · <a href='results/summary.json'>Summary JSON</a> · <a href='sources/provenance.json'>Sources and hashes</a></p><p class='meta'>Public sources were downloaded for this local research experiment. Video and PDF rights remain with their source owners; CurlR's CC0 applies to the dataset. No content was published or redistributed.</p></footer></main></html>"""
(R / "report.html").write_text(report)
print("Built report.html and two reproducible figures.")
