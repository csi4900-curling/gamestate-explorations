# Bright-body cap proposal probe — development only

The previously frozen cap proposal requires a dark neutral surround. In the
Slovakia–USA Beijing 2022 G02 yellow delivery, the moving cap is visible at
about 3960–3965 s, but the surround often appears bright on ice; in one frame
the cap joins a large yellow rink graphic. This probe permits a cap with low
neutral surround when at least 65% of its surrounding patch resembles bright
ice. The default detector remains unchanged. The new option is explicitly
`--bright-body-probe` in `scan_beijing_layout_gaps.py`, and neither output is
promoted to a confirmed throw timeline.

The rule was chosen after inspecting the Slovakia–USA failure. All results
below are **post-score development diagnostics** on already exposed sources and
agent-authored coarse references. They are not held-out event F1 estimates.

| Source / scored gap | Proposal stage | Raw TP / FP / FN | Screened TP / FP / FN | Screened candidate F1 |
| --- | --- | ---: | ---: | ---: |
| Slovakia–USA, three interior gaps, 7 coarse throws | frozen | 5 / 15 / 2 | 4 / 3 / 3 | 0.571 |
| Slovakia–USA, same gaps | bright-body | 7 / 25 / 0 | 5 / 2 / 2 | 0.714 |
| Sweden–Switzerland, one interior gap, 1 coarse throw | frozen | 1 / 3 / 0 | 1 / 0 / 0 | 1.000 |
| Sweden–Switzerland, same gap | bright-body | 1 / 4 / 0 | 1 / 0 / 0 | 1.000 |

The Slovakia–USA raw recall gain comes with ten additional false candidates.
Even after the old ice/episode screen, two throws are missed. The one-window
Swiss score has essentially no power to show generalization.

On the exposed Canada–China 2022 interior gap (3600–3900 s), the old scanner
emitted one yellow track at 3668–3671 s and its development screen retained
it. The bright-body scanner emitted 12 tracks. Its unchanged screen retained
two **red** tracks at 3642 and 3880 s and withheld the visible yellow track.
There is no exhaustive coarse reference for that entire gap, so no F1 is
reported. This regression is enough to reject simple threshold relaxation as
the next confirmed detector. It points to the need for stone identity and
delivery-origin evidence across camera cuts, rather than selecting the first
locally plausible motion track in a long episode.

Reproducibility: candidate and screen artifacts are beside their source
benchmarks: [Slovakia–USA](../slovakia-usa22-gap-transfer/),
[Sweden–Switzerland](../swiss22-gap-transfer/), and
[Canada–China](../full-china22-partial/). The two scored comparisons are
`postscore-bright-body-comparison.json`; the Slovakia–USA frozen baseline is
`postscore-baseline-comparison.json`. Artifacts record source, input, model and
runner hashes. The comparator is `prototype/scripts/score_gap_probe.py` and
scores only the declared subintervals, excluding uncertain gap boundaries.

The scanner's default mode was rerun on the Swiss gap after this code change;
its four candidate objects are identical to the frozen original. All 142
prototype tests and Ruff checks passed.
